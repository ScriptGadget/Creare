# !/usr/bin/env python
#  Copyright 2011 Bill Glover
#
#  This file is part of Creare.
#
#  Creare is free software: you can redistribute it and/or modify it
#  under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  Creare is distributed in the hope that it will be useful, but
#  WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with Creare.  If not, see <http://www.gnu.org/licenses/>.
#
import os
from google.appengine.dist import use_library
use_library('django', '0.96')

import logging
from datetime import datetime
import hashlib
import urllib
from operator import attrgetter

from django.utils import simplejson

from google.appengine.api import images
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp import util
from google.appengine.api import users
from google.appengine.ext import db
from google.appengine.api import memcache
from google.appengine.datastore import entity_pb

from gaesessions import get_current_session

from model import *
from forms import *
from payment import *
from authentication import Authenticator

template.register_template_library('common.catalog_tag')


# some settings
MAX_PRODUCT_IMAGE_HEIGHT=320
MAX_PRODUCT_IMAGE_WIDTH=320


# These two methods are from an article at
# http://blog.notdot.net/2009/9/Efficient-model-memcaching
def serialize_entities(models):
    "Convert db.Models into protobufs which work great in Memcached"
    if models is None:
        return None
    elif isinstance(models, db.Model):
        # Just one instance
        return db.model_to_protobuf(models).Encode()
    else:
        # A list
        return [db.model_to_protobuf(x).Encode() for x in models]

def deserialize_entities(data):
    "Convert a protobuf or list of protobufs into db.Models"
    if data is None:
        return None
    elif isinstance(data, str):
        # Just one instance
        return db.model_from_protobuf(entity_pb.EntityProto(data))
    else:
        return [db.model_from_protobuf(entity_pb.EntityProto(x)) for x in data]

def add_base_values(template_values):
    community = Community.get_current_community()

    if community:
        if not 'community' in template_values:
            template_values['community'] = community
        q = db.Query(NewsItem)
        q.filter('show =', True).order('-created')
        news_items = q.fetch(limit=3)
        template_values["news_items"] = news_items

    user = users.get_current_user()
    template_values["user"] = user

    if 'maker' not in template_values:
        template_values['maker'] = Maker.getMakerForUser(user)
    
    if users.is_current_user_admin():
        template_values['admin'] = True

    items = get_current_session().get('ShoppingCartItems', [])
    count = 0
    if items != ():
        for item in items:
            count += item.count

    template_values['cartItems'] = count
    return template_values;

def buildImageUploadForm(prompt="Upload Image: (PNG or JPG, %(height)sx%(width)s, less then 1MB)", name="img", height=MAX_PRODUCT_IMAGE_HEIGHT, width=MAX_PRODUCT_IMAGE_WIDTH, count=1):
    """ Build a form to upload images with a configurable prompt message. """
    new_prompt = prompt % {'height':height, 'width':width}
    return """
<div><label>%(prompt)s</label></div> 
<div><input type="file" name="%(name)s"/></div>
""" % {'prompt':new_prompt, 'name':name}

def buildTagField(value):
    return """<tr><th><label for="id_tags">%s: </label></th><td><input type="text" name="tags" value="%s" id="id_tags" /></td></tr>""" % (Product.tags.verbose_name, value)

def write_error_page(handler, message):
    handler.error(403)
    template_values = {"message":message}
    path = os.path.join(os.path.dirname(__file__), "templates/error.html")
    handler.response.out.write(template.render(path, add_base_values(template_values)))


class MakerPage(webapp.RequestHandler):
    """ A page for adding a Maker  """
    prompt_base = "%s: (PNG or JPG, %dwx%dh, less than 1MB)"
    message_base = "That doesn't seem to be a valid %s. Images must be PNG or JPG files and be less than 1MB. Try resizing until the image fits in a rectangle %d pixels high by %d pixels wide. (It can be smaller)"
    photo_height = 110 
    photo_width = 110
    photo_prompt =  prompt_base % ("Your Photo", photo_width, photo_height)
    photo_message = message_base % ('photo', photo_height, photo_width)

    logo_height= 60
    logo_width= 190
    logo_prompt = prompt_base % ("Your Logo Banner", logo_width, logo_height)
    logo_message = message_base  % ('logo', logo_height, logo_width)
    
    def get(self):
        authenticator = Authenticator(self)

        try:
            (user, maker) = authenticator.authenticate()
        except:
            # Return immediately
            return

        if user and maker:
            self.redirect('/maker_dashboard/' + maker.slug)
            return
        else:
            data = MakerForm()
            template_values = { 'title':'Open Your Store',
                                'form':data,
                                'tag_field':buildTagField(''),
                                'max_width_photo': MakerPage.photo_width,
                                'max_height_photo': MakerPage.photo_height,
                                'max_width_logo': MakerPage.logo_width,
                                'max_height_logo': MakerPage.logo_height,
                                'uri':self.request.uri}
            path = os.path.join(os.path.dirname(__file__), "templates/maker.html")
            self.response.out.write(template.render(path, add_base_values(template_values)))

    def post(self):
        session = get_current_session()
        community = Community.get_current_community()

        if not community:
            self.error(404)
            self.response.out.write("I don't recognize that community")
            return

        data = MakerForm(data=self.request.POST)
        accepted_terms = self.request.get('term1')

        temp_key = self.request.get("photo")
        if temp_key is None or temp_key == '':
            photo_is_valid = True
            photo = None
        else:
            photo = db.get(temp_key)
            if photo is not None:
                photo_is_valid = True;

        temp_key = self.request.get("logo")
        if temp_key is None or temp_key == '':
            logo_is_valid = True
            logo = None
        else:
            logo = db.get(temp_key)
            if logo is not None:
                logo_is_valid = True;

        if data.is_valid() and accepted_terms and photo_is_valid and logo_is_valid:
            # Save the data, and redirect to the view page
            entity = data.save(commit=False)
            entity.user = users.get_current_user()
            entity.community = community
            entity.slug = Maker.get_slug_for_store_name(entity.store_name)
            entity.accepted_terms = bool(accepted_terms)
            tags = self.request.get("tags").split(',')
            entity.tags = []
            for tag in tags:
                entity.tags.append(tag.strip().lower())
            entity.put()
            if photo:
                Image( 
                    parent=entity, 
                    category='Portrait',
                    content=photo.content,
                    ).put()
                photo.delete()
            if logo:
                Image( 
                    parent=entity, 
                    category='Logo',
                    content=logo.content,
                    ).put()
                logo.delete()
            community.increment_maker_score()
            self.redirect('/maker_dashboard/' + entity.slug)
        else:
            messages = []
            if not photo_is_valid:
                messages.append(MakerPage.photo_message)
            if not logo_is_valid:
                messages.append(MakerPage.logo_message)

            if not accepted_terms:
                messages.append('You must accept the terms and conditions to use this site.')
            # Reprint the form
            template_values = { 'title':'Open Your Store', 
                                'messages':messages,
                                'tag_field':buildTagField(self.request.get('tags')),
                                'max_width_photo': MakerPage.photo_width,
                                'max_height_photo': MakerPage.photo_height,
                                'max_width_logo': MakerPage.logo_width,
                                'max_height_logo': MakerPage.logo_height,
                                'form' : data, 
                                'uri': self.request.uri}
            path = os.path.join(os.path.dirname(__file__), "templates/maker.html")
            logging.info("Showing Registration Page")
            self.response.out.write(template.render(path, add_base_values(template_values)))

class EditMakerPage(webapp.RequestHandler):
    """ Edit a Maker store """

    def get(self, maker_slug):
        if not maker_slug:
            logging.info('No id found for EditMakerPage')
            maker = Maker.getMakerForUser(users.get_current_user())
            if maker:
                maker_slug = maker.slug
            else:
                self.error(404)
                self.response.out.write("I don't recognize that maker.")
                return
        else:
            try:
                maker = Maker.get_maker_for_slug(maker_slug)
            except:
                self.error(404)
                self.response.out.write("I don't recognize that maker.")
                return

        if maker and Authenticator.authorized_for(maker.user):
            if len(maker.tags):
                tags = ', '.join(maker.tags)
            else:
                tags = ''
            template_values = { 'form' : MakerForm(instance=maker),
                                'id' : maker.key(),
                                'tag_field':buildTagField(tags),
                                'max_width_photo': MakerPage.photo_width,
                                'max_height_photo': MakerPage.photo_height,
                                'max_width_logo': MakerPage.logo_width,
                                'max_height_logo': MakerPage.logo_height,
                                'uri':self.request.uri,
                                'title':'Update Store Information'}
            path = os.path.join(os.path.dirname(__file__), "templates/maker.html")
            self.response.out.write(template.render(path, add_base_values(template_values)))
        else:
            self.redirect('/maker/add')

    def post(self, id):
        session = get_current_session()
        community = Community.get_current_community()

        if not community:
            self.error(404)
            self.response.out.write("I don't recognize that community")
            return

        id = self.request.get('_id')
        maker = Maker.get(id)
        if not Authenticator.authorized_for(maker.user):
            self.redirect('/maker/add')
        else:
            data = MakerForm(data=self.request.POST, instance=maker)
            temp_key = self.request.get("photo")
            if temp_key is None or temp_key == '':
                photo_is_valid = True
                photo = None
            else:
                photo = db.get(temp_key)
                if photo is not None:
                    photo_is_valid = True;

            temp_key = self.request.get("logo")
            if temp_key is None or temp_key == '':
                logo_is_valid = True
                logo = None
            else:
                logo = db.get(temp_key)
                if logo is not None:
                    logo_is_valid = True;

            if data.is_valid() and photo_is_valid and logo_is_valid:
                entity = data.save(commit=False)
                entity.user = users.get_current_user()
                entity.slug = Maker.get_slug_for_store_name(entity.store_name)
                tags = self.request.get("tags").split(',')
                entity.tags=[]
                for tag in tags:
                    entity.tags.append(tag.strip().lower())
                entity.put()
                if photo:
                    if maker.photo:
                        db.delete(maker.photo)
                    Image(
                        parent=entity,
                        category='Portrait',
                        content=photo.content,
                        ).put()
                    photo.delete()
                if logo:
                    if maker.logo:
                        db.delete(maker.logo)
                    Image(
                        parent=entity,
                        category='Logo',
                        content=logo.content,
                        ).put()
                    logo.delete()
                self.redirect('/maker_dashboard/' + entity.slug)
            else:
                messages = []
                if not photo_is_valid:
                    messages.append(MakerPage.photo_message)
                if not logo_is_valid:
                    messages.append(MakerPage.logo_message)
                # Reprint the form
                template_values = { 'form' : data,
                                    'id' : id,
                                    'messages':messages,
                                    'tag_field':buildTagField(self.request.get('tags')),
                                    'max_width_photo': MakerPage.photo_width,
                                    'max_height_photo': MakerPage.photo_height,
                                    'max_width_logo': MakerPage.logo_width,
                                    'max_height_logo': MakerPage.logo_height,
                                    'uri':self.request.uri,
                                    'title':'Update Store Information',
                                    }
                path = os.path.join(os.path.dirname(__file__), "templates/maker.html")
                self.response.out.write(template.render(path, add_base_values(template_values)))

class ProductPage(webapp.RequestHandler):
    """ Add a Product """

    def get(self):
        authenticator = Authenticator(self)

        try:
            (user, maker) = authenticator.authenticate()
        except:
            # Return immediately
            return

        if not user or not maker or not maker.approval_status == 'Approved':
            self.error(403)
            self.response.out.write("You do not have permission to add products.")
            return
        else:
            template_values = { 'form' : ProductForm(maker=maker), 
                                'tag_field':buildTagField(''),
                                'max_width':MAX_PRODUCT_IMAGE_WIDTH,
                                'max_height':MAX_PRODUCT_IMAGE_HEIGHT,
                                'uri':self.request.uri}
            path = os.path.join(os.path.dirname(__file__), "templates/product.html")
            self.response.out.write(template.render(path, add_base_values(template_values)))

    def post(self):
        authenticator = Authenticator(self)

        try:
            (user, maker) = authenticator.authenticate()
        except:
            # Return immediately
            return

        if not user or not maker or not maker.approval_status == 'Approved':
            self.error(403)
            self.response.out.write("You do not have permission to add products.")
            return
        else:
            data = ProductForm(data=self.request.POST, maker=maker)
            image_key = self.request.get("img0")
            image_is_valid = image_key is not None and image_key != ''

            if data.is_valid() and image_is_valid:
                entity = data.save(commit=False)
                entity.maker = maker
                entity.slug = Product.get_slug_for_name(entity.name)
                entity.when = Product.buildWhenStamp(maker)
                if entity.unique:
                    entity.inventory = 1
                tags = self.request.get("tags").split(',')
                entity.tags = []
                for tag in tags:
                    entity.tags.append(tag.strip().lower())
                entity.put()
                temp_image = db.get(image_key)
                primary_image = Image(
                    parent=entity,
                    category='Product',
                    content=temp_image.content,
                    )
                primary_image.put()
                temp_image.delete()
                entity.primary_image = primary_image
                entity.put()
                Community.get_current_community().increment_product_score()
                self.redirect('/maker_dashboard/' + maker.slug)
            else:
                messages = []
                if not image_is_valid:
                    messages.append("That doesn't seem to be a valid image. Images must be PNG or JPG files and be less than 1MB. Try resizing until the image fits in a square %(height)s pixels high by %(width)s pixels wide." % {'height':MAX_PRODUCT_IMAGE_HEIGHT, 'width':MAX_PRODUCT_IMAGE_WIDTH})

                # Reprint the form
                template_values = { 'form' : data,
                                    'tag_field':buildTagField(self.request.get('tags')),
                                    'messages':messages,
                                    'max_width':MAX_PRODUCT_IMAGE_WIDTH,
                                    'max_height':MAX_PRODUCT_IMAGE_HEIGHT,
                                    'uri':self.request.uri}
                path = os.path.join(os.path.dirname(__file__), "templates/product.html")
                self.response.out.write(template.render(path, add_base_values(template_values)))

class EditProductPage(webapp.RequestHandler):
    """ Edit an existing Product """

    def get(self, maker_slug, product_slug):
        authenticator = Authenticator(self)

        try:
            (user, maker) = authenticator.authenticate()
        except:
            # Return immediately
            return

        if not maker:
            session = get_current_session()
            community = Community.get_current_community()

            if not community:
                self.error(404)
                self.response.out.write("I don't recognize that community.")
                return
            self.error(403)
            self.response.out.write("You do not have permission to edit that product.")
            return
        else:
            product = Product.get_product_for_slug(product_slug)

            if not Authenticator.authorized_for(product.maker.user) or not maker.approval_status == 'Approved':
                self.error(403)
                self.response.out.write("You do not have permission to edit that product.")
                return

            if len(maker.tags):
                tags = ', '.join(product.tags)
            else:
                tags = ''
            template_values = { 'form' : ProductForm(instance=product),
                                'tag_field':buildTagField(tags),
                                'product':product,
                                'id' : product.key(),
                                'max_width':MAX_PRODUCT_IMAGE_WIDTH,
                                'max_height':MAX_PRODUCT_IMAGE_HEIGHT,
                                'uri':self.request.uri}
            path = os.path.join(os.path.dirname(__file__), "templates/product.html")
            self.response.out.write(template.render(path, add_base_values(template_values)))

    def post(self, maker_slug, product_slug):
      _id = self.request.get('_id')
      product = Product.get(_id)
      authenticator = Authenticator(self)

      try:
          (user, maker) = authenticator.authenticate()
      except:
          # Return immediately
          return

      if not Authenticator.authorized_for(product.maker.user) or not maker.approval_status == 'Approved':
          logging.error('Illegal attempt to edit product owned by: ' + product.maker.full_name + ' by ' + str(user.get_current_user()))
          self.redirect('/')
          return
      else:
          data = ProductForm(data=self.request.POST, instance=product)
          image_key = self.request.get("img0")
          image_is_valid = True

          if data.is_valid() and image_is_valid:
              entity = data.save(commit=False)
              entity.slug = Product.get_slug_for_name(entity.name)
              if entity.unique:
                  entity.inventory = 1
              tags = self.request.get("tags").split(',')
              entity.tags = []
              for tag in tags:
                  entity.tags.append(tag.strip().lower())

              temp_image = None;
              if image_key is not None and image_key != '':
                  temp_image = db.get(image_key)
              if temp_image:
                  if product.image:
                      db.delete(product.image)
                  primary_image = Image(
                      parent=entity,
                      category='Product',
                      content=temp_image.content,
                      )
                  primary_image.put()
                  temp_image.delete()
                  entity.primary_image = primary_image
              entity.put()
              self.redirect('/maker_dashboard/' + maker.slug)
          else:
              messages = []
              if not image_is_valid:
                  messages.append("That doesn't seem to be a valid image. Images must be PNG or JPG files and be less than 1MB. Try resizing until the image fits in a square %(height)s pixels high by %(width)s pixels wide." % {'height':MAX_PRODUCT_IMAGE_HEIGHT, 'width':MAX_PRODUCT_IMAGE_WIDTH})
              # Reprint the form
              template_values = { 'form' : data,
                                  'tag_field':buildTagField(self.request.get('tags')),
                                  'messages': messages,
                                  'product':product,
                                  'id' : _id,
                                  'max_width':MAX_PRODUCT_IMAGE_WIDTH,
                                  'max_height':MAX_PRODUCT_IMAGE_HEIGHT,
                                  'uri':self.request.uri}
              path = os.path.join(os.path.dirname(__file__), "templates/product.html")
              self.response.out.write(template.render(path, add_base_values(template_values)))

class ViewProductPage(webapp.RequestHandler):
    """ View a Product """
    def get(self, maker_slug, product_slug):
        community = Community.get_current_community()

        if not community:
            self.error(404)
            self.response.out.write("I don't recognize that community.")
            return

        product = Product.get_product_for_slug(product_slug)
        if product and (product.disable or not product.show):
            product = None

        if not product:
            self.error(404)
            self.response.out.write("I don't recognize that product.")
            return

        template_values = { 
            'title' : product.name,
            'store' : product.maker,
            'product':product,
            'url':self.request.url,
            }
        path = os.path.join(os.path.dirname(__file__), "templates/view_product.html")
        self.response.out.write(template.render(path, add_base_values(template_values)))

class Login(webapp.RequestHandler):
    """ Just authenticates then redirects to the home page """
    def get(self):
        authenticator = Authenticator(self)
        community = Community.get_current_community()

        try:
            (user, maker) = authenticator.authenticate()
        except:
            # Return immediately
            return

        session = get_current_session()
        session['community'] = community.slug
        # session.start(ssl_only=True)
        session.regenerate_id()

        if maker:
            self.redirect('/maker_dashboard/%s' % maker.slug)
        else:
            if users.is_current_user_admin():
                self.redirect('/')
            else:
                self.redirect('/maker/add')

class Logout(webapp.RequestHandler):
    """ Just kills the session and clears authentication tokens  """
    def get(self):
        session = get_current_session()
        community = session.get('community')
        session.clear()
        if community:
            session['community'] = community
        self.redirect(users.create_logout_url('/'))

class CommunityHomePage(webapp.RequestHandler):
    """ Renders the home page template. """
    def get(self):
        session = get_current_session()
        community = Community.get_current_community()

        if not community:
            self.redirect('/community/add')
            return

        session['community'] = community.slug

        featured_maker = deserialize_entities(memcache.get("featured_maker"))
        featured_products = deserialize_entities(memcache.get("featured_products"))
        if not featured_maker:
            (featured_maker, featured_products) = Product.getFeatured(4, community)
            cache_map = { "featured_maker" : serialize_entities(featured_maker),
                          "featured_products" : serialize_entities(featured_products)}
            memcache.set_multi(cache_map, time=3600)

        template_values = { 
            'title': community.name,
            'latest': Product.getLatest(4),
            'featured_products': featured_products,
            'featured_maker': featured_maker,
            'categories':sorted(community.categories),
            'width': 4,
            'url':self.request.url,
            }

        path = os.path.join(os.path.dirname(__file__), "templates/home.html")
        self.response.out.write(template.render(path, add_base_values(template_values)))

class MakerDashboard(webapp.RequestHandler):
    """ Renders a page for Makers to view and manage their catalog and sales """
    def get(self, maker_slug):
        authenticator = Authenticator(self)

        try:
            (user, maker) = authenticator.authenticate()
        except:
            # Return immediately
            return

        if not maker:
            self.redirect("/maker_store/" + maker_slug)
            return

        if not maker.slug == maker_slug:
            logging.info('=== MakerDashboard.get(): ' + maker.slug + ' does not equal ' + maker_slug)
            self.redirect("/maker_store/" + maker_slug)
            return
        else:
            q = db.Query(Advertisement)
            q.filter('show =', True).order('last_shown')

            ad = None
            for a in q:
                if a.PSA or a.remaining_impressions() > 0:
                    ad = a
                    break;
                else:
                    a.show = False
                    a.put()

            if ad:
                if not ad.PSA:
                    ad.decrement_impressions()
                ad.put() # to update the last_shown
                ad.img = '/images/' + str(ad.image)
                ad.width = AdvertisementPage.photo_width
                ad.height = AdvertisementPage.photo_height

            products = maker.products
            template_values = { 
                'title':'Maker Dashboard',
                'ad':ad,
                'store':maker,
                'products': sorted(products, key=attrgetter('when'), reverse=True),
                }
            path = os.path.join(os.path.dirname(__file__), "templates/maker_dashboard.html")
            self.response.out.write(template.render(path, add_base_values(template_values)))

class MakerStorePage(webapp.RequestHandler):
    """ Renders a store page for a particular maker. """
    def get(self, maker_slug):
        maker = Maker.get_maker_for_slug(maker_slug)
        products = []
        if maker:
            for product in maker.products:
                if product.show and not product.disable:
                    products.append(product)
        else:
            write_error_page(self, "I don't recognize that store.")
            return
        
        template_values = { 
            'title':maker.store_name,
            'store':maker,
            'products':sorted(products, key=attrgetter('when'), reverse=True),
            'user':users.get_current_user()
            }
        path = os.path.join(os.path.dirname(__file__), "templates/maker_store.html")
        self.response.out.write(template.render(path, add_base_values(template_values)))

class EditCommunityPage(webapp.RequestHandler):
    """ A page for managing community info  """
    def get(self):
        authenticator = Authenticator(self)

        try:
            (user, maker) = authenticator.authenticate()
        except AuthenticationException:
            return
        except Exception, e:
            self.error(500)
            self.response.out.write("Error identifying user: " + str(e))
            return

        if user and users.is_current_user_admin():
            community = Community.get_current_community()

            if not community:
                self.error(404)
                self.response.out.write("I don't recognize that community")
                return

            data = CommunityForm(instance=community)
            template_values = { 
                'title':'Create a Community',
                'community':community,
                'form':data,
                'id':community.key(),
                'uri':self.request.uri,
                'photo_upload_form':buildImageUploadForm(prompt=CommunityPage.photo_prompt, name="photo"),
                'logo_upload_form':buildImageUploadForm(prompt=CommunityPage.logo_prompt, name="logo"),
                }
            path = os.path.join(os.path.dirname(__file__), "templates/community.html")
            self.response.out.write(template.render(path, add_base_values(template_values)))

        else:
            self.error(403)
            self.response.out.write('You do not have permission to edit this community.')

    def post(self):
        authenticator = Authenticator(self)

        try:
            (user, maker) = authenticator.authenticate()
        except AuthenticationException:
            return
        except Exception, e:
            self.error(500)
            self.response.out.write("Error identifying user:" + str(e))
            # Return immediately
            return

        if user and users.is_current_user_admin():
            id = self.request.get('_id')
            community = Community.get(id)
            photo_file = self.request.get("photo")

            if not photo_file:
                photo_is_valid = True
                photo = None
            else:
                photo_is_valid = len(photo_file) < 1024*1024
                if photo_is_valid:
                    try:
                        photo = images.resize(photo_file, CommunityPage.photo_width, CommunityPage.photo_height)
                    except Exception, e:
                        photo = None
                        photo_is_valid = False

            logo_file = self.request.get("logo")

            if not logo_file:
                logo_is_valid = True
                logo = None
            else:
                logo_is_valid = len(logo_file) < 1024*1024
                if logo_is_valid:
                    try:
                        logo = images.resize(logo_file, CommunityPage.logo_width, CommunityPage.logo_height)
                    except:
                        logo = None
                        logo_is_valid = False

            data = CommunityForm(data=self.request.POST, instance=community)
            if data.is_valid() and photo_is_valid and logo_is_valid:
                # Save the data, and redirect to the view page
                entity = data.save(commit=False)
                entity.slug = Community.get_slug_for_name(entity.name)
                entity.put()
                if photo:
                    if community.photo:
                        db.delete(community.photo)
                    Image(
                        parent=entity,
                        category='Portrait',
                        content=photo,
                        ).put()
                if logo:
                    if community.logo:
                        db.delete(community.logo)
                    Image(
                        parent=entity,
                        category='Logo',
                        content=logo,
                        ).put()

                self.redirect('/')
            else:
                messages = []
                if not photo_is_valid:
                    messages.append(CommunityPage.photo_message)
                if not logo_is_valid:
                    messages.append(CommunityPage.logo_message)

                template_values = { 'title':'Create a Community',
                                    'id' : id,
                                    'messages':messages,
                                    'form' : data,
                                    'photo_upload_form':buildImageUploadForm(prompt=CommunityPage.photo_prompt, name="photo"),
                                    'logo_upload_form':buildImageUploadForm(prompt=CommunityPage.logo_prompt, name="logo"),
                                    'uri': self.request.uri}
                path = os.path.join(os.path.dirname(__file__), "templates/community.html")
                self.response.out.write(template.render(path, add_base_values(template_values)))
        else:
            self.error(403)
            self.response.out.write('You do not have permission to edit this community.')

class CommunityPage(webapp.RequestHandler):
    """ A page for adding a Community  """
    prompt_base = "%s: (PNG or JPG, %dwx%dh, less than 1MB)"
    message_base = "That doesn't seem to be a valid %s. Images must be PNG or JPG files and be less than 1MB. Try resizing until the image fits in a rectangle %d pixels high by %d pixels wide. (It can be smaller)"
    photo_height = 110 
    photo_width = 110
    photo_prompt =  prompt_base % ("Your Photo", photo_width, photo_height)
    photo_message = message_base % ('photo', photo_height, photo_width)

    logo_height= 108
    logo_width= 750
    logo_prompt = prompt_base % ("Your Logo Banner", logo_width, logo_height)
    logo_message = message_base  % ('logo', logo_height, logo_width)

    def get(self):
        if Community.get_current_community():
            self.redirect('/community/edit')
            return

        authenticator = Authenticator(self)

        try:
            (user, maker) = authenticator.authenticate()
        except AuthenticationException:
            return
        except Exception, e:
            self.error(500)
            self.response.out.write('Error identifying user:' + str(e))
            return

        if user and users.is_current_user_admin():
            data = CommunityForm()
            template_values = { 
                'title':'Create a Community',
                'form':data,
                'photo_upload_form':buildImageUploadForm(prompt=CommunityPage.photo_prompt, name="photo"),
                'logo_upload_form':buildImageUploadForm(prompt=CommunityPage.logo_prompt, name="logo"),
                'uri':self.request.uri,
                }
            path = os.path.join(os.path.dirname(__file__), "templates/community.html")
            self.response.out.write(template.render(path, add_base_values(template_values)))

        else:
            self.error(403)
            self.response.out.write('You do not have permission to create a new community.')


    def post(self):
        authenticator = Authenticator(self)
        try:
            (user, maker) = authenticator.authenticate()
        except:
            self.error(403)
            self.response.out.write('You do not have permission to create a new community.')
            return

        photo_file = self.request.get("photo")
        photo_is_valid = photo_file is not None and photo_file != ''
        photo_is_valid = photo_is_valid and len(photo_file) < 1024*1024
        if photo_is_valid:
            try:
                photo = images.resize(photo_file, CommunityPage.photo_width, CommunityPage.photo_height)
            except:
                photo_is_valid = False

        logo_file = self.request.get("logo")
        logo_is_valid = logo_file is not None and logo_file != ''
        logo_is_valid = logo_is_valid and len(logo_file) < 1024*1024
        if logo_is_valid:
            try:
                logo = images.resize(logo_file, CommunityPage.logo_width, CommunityPage.logo_height)
            except:
                logo_is_valid = False

        data = CommunityForm(data=self.request.POST)
        if data.is_valid() and photo_is_valid and logo_is_valid:
            # Save the data, and redirect to the view page
            entity = data.save(commit=False)
            entity.slug = Community.get_slug_for_name(entity.name)
            entity.put()
            if photo:
                Image( 
                    parent=entity, 
                    category='Portrait',
                    content=photo,
                    ).put()
            if logo:
                Image( 
                    parent=entity, 
                    category='Logo',
                    content=logo,
                    ).put()
            self.redirect('/')
        else:
            messages = []
            if not photo_is_valid:
                messages.append(MakerPage.photo_message)
            if not logo_is_valid:
                messages.append(MakerPage.logo_message)

            template_values = { 
                'title':'Create a Community',
                'messages':messages,
                'photo_upload_form':buildImageUploadForm(prompt=CommunityPage.photo_prompt, name="photo"),
                'logo_upload_form':buildImageUploadForm(prompt=CommunityPage.logo_prompt, name="logo"),
                'form' : data,
                'uri': self.request.uri
                }
            path = os.path.join(os.path.dirname(__file__), "templates/community.html")
            self.response.out.write(template.render(path, add_base_values(template_values)))

class SiteHomePage(webapp.RequestHandler):
    """ A site root page """
    def get(self):
        communities = Community.all()
        message = '<h2>Please visit one of our communities</h2>'
        for community in communities:
            message += '<p><a href="%s">%s</a></p>' % ('/',community.name)
        self.response.out.write(message)

class CheckoutPage(webapp.RequestHandler):
    """ Note that we remember the price at the moment the item was added to the
    shopping cart, not nececarily the price of the product as it is in the datastore
    at the moment of checkout. """
    def get(self):
        session = get_current_session()
        if not session.is_active():
            self.response.out.write("I don't see anything in your cart")
            return
        else:
            community = Community.get_current_community()        
            if not community:
                self.error(404)
                self.response.out.write("I don't recognize that community")
                return

            template_values = { 'title':'Checkout',
                                'uri':self.request.uri}
            path = os.path.join(os.path.dirname(__file__), "templates/checkout.html")
            self.response.out.write(template.render(path, add_base_values(template_values)))

    def post(self):
        pass

class NotFoundErrorHandler(webapp.RequestHandler):
    """ A site root page """
    def get(self):
        self.error(404)
        self.response.out.write("Opps, that doesn't seem to be a valid page.")

class ListNewsItems(webapp.RequestHandler):
    """ List news items. """
    def get(self):
        session = get_current_session()

        q = db.Query(NewsItem)
        if not users.is_current_user_admin():
            q.filter('show =', True)

        items = q.fetch(50)

        template_values = { 
            'title':'News Items', 
            'items': items, 
            }
        path = os.path.join(os.path.dirname(__file__), "templates/news_items.html")
        self.response.out.write(template.render(path, add_base_values(template_values)))


class ViewNewsItem(webapp.RequestHandler):
    """ View an existing item. """
    def get(self, slug):
        news_item = NewsItem.get_news_item_for_slug(slug)
        q = NewsItem.all()
        if not users.is_current_user_admin():
            q.filter('show =', True)
        news_items = q.fetch(limit=3)
        template_values = { 'title':'News',
                            'news_item':news_item,
                            'news_items':news_items,
                            'uri':self.request.uri}
        path = os.path.join(os.path.dirname(__file__), "templates/news_item.html")
        self.response.out.write(template.render(path, add_base_values(template_values)))


class EditNewsItem(webapp.RequestHandler):
    """ Edit an existing news item. """
    def get(self, slug):
        authenticator = Authenticator(self)
        try:
            (user, maker) = authenticator.authenticate()
        except:
            # Return immediately
            return

        if user: # Need to authorize community coordinators
            news_item = NewsItem.get_news_item_for_slug(slug)
            id = news_item.key()
            data = NewsItemForm(instance=news_item)
            q = NewsItem.all()
            q.filter('show =', True)
            news_items = q.fetch(limit=3)
            template_values = { 'title':'News',
                                'form':data,
                                'id':id,
                                'news_items':news_items,
                                'uri':self.request.uri}
            path = os.path.join(os.path.dirname(__file__), "templates/news_item.html")
            self.response.out.write(template.render(path, add_base_values(template_values)))

        else:
            self.error(403)
            self.response.out.write('You do not have permission to create a new news item for this community.')

    def post(self, slug):
        authenticator = Authenticator(self)
        try:
            (user, maker) = authenticator.authenticate()
        except:
            self.error(403)
            self.response.out.write('You do not have permission to create a new community.')
            return

        id = self.request.get('_id')
        news_item = NewsItem.get(id)
        data = NewsItemForm(data=self.request.POST, instance=news_item)

        if data.is_valid():
            entity = data.save(commit=False)
            entity.slug = NewsItem.get_slug_for_title(entity.title)
            entity.put()
            self.redirect('/news_item/' + entity.slug)
        else:
            # Reprint the form
            template_values = { 'title':'Create a NewsItem',
                                'form' : data,
                                'id': id,
                                'uri': self.request.uri}
            path = os.path.join(os.path.dirname(__file__), "templates/news_item.html")
            self.response.out.write(template.render(path, add_base_values(template_values)))

class AddNewsItem(webapp.RequestHandler):
    """ Add a new news item. """
    def get(self):
        authenticator = Authenticator(self)
        try:
            (user, maker) = authenticator.authenticate()
        except:
            # Return immediately
            return

        if users.is_current_user_admin():
            data = NewsItemForm()
            template_values = { 'title':'Create a News Item',
                                'form':data,
                                'uri':self.request.uri}
            path = os.path.join(os.path.dirname(__file__), "templates/news_item.html")
            self.response.out.write(template.render(path, add_base_values(template_values)))

        else:
            self.error(403)
            self.response.out.write('You do not have permission to create a new news item for this community.')


    def post(self):
        authenticator = Authenticator(self)
        try:
            (user, maker) = authenticator.authenticate()
        except:
            self.error(403)
            self.response.out.write('You do not have permission to create a new community.')
            return

        data = NewsItemForm(data=self.request.POST)
        if data.is_valid():
            entity = data.save(commit=False)
            session = get_current_session()
            community = Community.get_current_community()

            if not community:
                self.error(404)
                self.response.out.write("I don't recognize that community")
                return
            entity.community = community
            entity.slug = NewsItem.get_slug_for_title(entity.title)
            entity.put()
            self.redirect('/news_item/' + entity.slug)
        else:
            # Reprint the form
            template_values = { 'title':'Create a NewsItem',
                                'form' : data,
                                'id' : id,
                                'uri': self.request.uri}
            path = os.path.join(os.path.dirname(__file__), "templates/news_items.html")
            self.response.out.write(template.render(path, add_base_values(template_values)))

class AdvertisementPage(webapp.RequestHandler):
    """ Add a Advertisement """
    prompt_base = "%s: (PNG or JPG, %dwx%dh, less than 1MB)"
    message_base = "That doesn't seem to be a valid %s. Images must be PNG or JPG files and be less than 1MB. Try resizing until the image fits in a rectangle %d pixels high by %d pixels wide. (It can be smaller)"
    photo_height = 160
    photo_width = 750
    photo_prompt =  prompt_base % ("Advertisement image", photo_width, photo_height)
    photo_message = message_base % ('image', photo_height, photo_width)

    @staticmethod
    def buildImageUploadForm():
        return buildImageUploadForm(AdvertisementPage.photo_prompt)

    def get(self):
        authenticator = Authenticator(self)


        if not users.is_current_user_admin():
            self.error(403)
            self.response.out.write("You do not have permission to add advertisements")
            return
        else:
            template_values = { 'form' : AdvertisementForm(),
                                'upload_form': AdvertisementPage.buildImageUploadForm(), 
                                'impressions':0,
                                'uri':self.request.uri}
            path = os.path.join(os.path.dirname(__file__), "templates/advertisement.html")
            self.response.out.write(template.render(path, add_base_values(template_values)))

    def post(self):
        authenticator = Authenticator(self)

        try:
            (user, maker) = authenticator.authenticate()
        except:
            # Return immediately
            return

        if not users.is_current_user_admin():
            self.error(403)
            self.response.out.write("You do not have permission to add advertisements")
            return
        else:
            session = get_current_session()
            community = Community.get_current_community()

            data = AdvertisementForm(data=self.request.POST)
            if data.is_valid():
                entity = data.save(commit=False)
                entity.community = community
                entity.slug = Advertisement.get_slug_for_name(entity.name)
                entity.put()
                try:
                  Image(
                      parent=entity,
                      category='Advertisement',
                      content=images.resize(self.request.get("img"), AdvertisementPage.photo_width, AdvertisementPage.photo_height),
                      ).put()
                except:
                    entity.delete()
                    self.response.out.write(AdvertisementPage.photo_message);
                    return
                impressions = int(self.request.get("impressions"))
                if impressions:
                    entity.refill_impressions(impressions)
                self.redirect('/advertisement/'+entity.slug)
            else:
                # Reprint the form
                template_values = { 'form' : data, 
                                    'upload_form': AdvertisementPage.buildImageUploadForm(),
                                    'impressions':0,
                                    'uri':self.request.uri}
                path = os.path.join(os.path.dirname(__file__), "templates/advertisement.html")
                self.response.out.write(template.render(path, add_base_values(template_values)))

class EditAdvertisementPage(webapp.RequestHandler):
    """ Edit an existing Advertisement """

    def get(self, advertisement_slug):
        if not users.is_current_user_admin():
            self.error(403)
            self.response.out.write('You do not have permission to edit advertisements.')
            return
        else:
            advertisement = Advertisement.get_advertisement_for_slug(advertisement_slug)

            template_values = { 'form' : AdvertisementForm(instance=advertisement), 
                                'upload_form': AdvertisementPage.buildImageUploadForm(),
                                'advertisement':advertisement,
                                'impressions':advertisement.remaining_impressions(),
                                'id' : advertisement.key(),
                                'uri':self.request.uri}
            path = os.path.join(os.path.dirname(__file__), "templates/advertisement.html")
            self.response.out.write(template.render(path, add_base_values(template_values)))

    def post(self, advertisement_slug):
      _id = self.request.get('_id')      
      advertisement = Advertisement.get(_id)

      if not users.is_current_user_admin():
          logging.error('Illegal attempt to edit advertisement: ' + advertisement.slug)
          self.error(403)
          self.response.out.write("You do not have permission to edit that product.")
          return
      else:
          data = AdvertisementForm(data=self.request.POST, instance=advertisement)
          if data.is_valid():
              entity = data.save(commit=False)
              entity.slug = Advertisement.get_slug_for_name(entity.name)
              entity.put()
              image = self.request.get("img")
              if image:
                  if advertisement.image:
                      db.delete(advertisement.image)
                  try:
                      Image(
                          parent=entity,
                          category='Advertisement',
                          content=images.resize(self.request.get("img"), AdvertisementPage.photo_width, AdvertisementPage.photo_height),
                          ).put()
                  except:
                    self.response.out.write(AdvertisementPage.photo_message);
                    return
              impressions = int(self.request.get("impressions"))
              if impressions:
                  entity.refill_impressions(impressions)
              self.redirect('/advertisements')
          else:
              # Reprint the form
              template_values = { 'form' : AdvertisementForm(instance=advertisement), 
                                  'id' : id, 
                                  'uri':self.request.uri}
              path = os.path.join(os.path.dirname(__file__), "templates/advertisement.html")
              self.response.out.write(template.render(path, add_base_values(template_values)))

class ViewAdvertisementPage(webapp.RequestHandler):
    """ View a Advertisement """
    def get(self, advertisement_slug):
        session = get_current_session()
        community = Community.get_current_community()
        
        if not community:
            self.error(404)
            self.response.out.write("I don't recognize that community.")
            return

        advertisement = Advertisement.get_advertisement_for_slug(advertisement_slug)
        if not advertisement:
            self.error(404)
            self.response.out.write("I don't recognize that advertisement.")
            return
            
        template_values = {'advertisement':advertisement}
        path = os.path.join(os.path.dirname(__file__), "templates/view_advertisement.html")
        self.response.out.write(template.render(path, add_base_values(template_values)))

class ListAdvertisements(webapp.RequestHandler):
    """ List news items. """
    def get(self):
        session = get_current_session()
        community = Community.get_current_community()
        
        if not community:
            self.error(404)
            self.response.out.write("I don't recognize that community")
            return

        template_values = { 'title':'Ads', 
                            'ads': community.community_advertisements
                            }
        path = os.path.join(os.path.dirname(__file__), "templates/advertisements.html")
        self.response.out.write(template.render(path, add_base_values(template_values)))

class ListMakers(webapp.RequestHandler):
    """ List makers. """
    def get(self):
        authenticator = Authenticator(self)

        try:
            (user, maker) = authenticator.authenticate()
        except:
            # Return immediately
            return

        if not users.is_current_user_admin():
            self.error(403)
            self.response.out.write("You don't have permission to coordinate Makers.")
            
        session = get_current_session()
        community = Community.get_current_community()
        
        if not community:
            self.error(404)
            self.response.out.write("I don't recognize that community")
            return

        makers = Maker.all()
        makers.order('-joined')

        template_values = { 
            'title':'Makers', 
            'makers':makers,
            'statusList':Maker.approval_status.choices,
            }
        path = os.path.join(os.path.dirname(__file__), "templates/makers.html")
        self.response.out.write(template.render(path, add_base_values(template_values)))

class CompletePurchase(webapp.RequestHandler):
    """ Handle a redirect from Paypal for a successful purchase. """
    def handle(self):
        if self.request.uri.count('cancel') > 0:
            Community.get_current_community().decrement_pending_score()
            message = "Checkout cancelled.";
        else:
            message = "Thank you for supporting local makers, crafters and artists.";
        
        write_error_page(self, message)

    def get(self):
        self.handle()

    def post(self):
        self.handle()

class RenderContentPage(webapp.RequestHandler):
    """ Render a content page. """
    def get(self, page_name):
        page = Page.get_or_insert(page_name, name=page_name)
        content = page.content.encode('utf-8')
        logging.info("content: '%s'", content)

        if not content or content.isspace():
            content = 'Please Add Content Here'

        template_values = { 'title':page.name, 
                            'name':page.name,
                            'content':content,
                            'uri':self.request.uri }
        path = os.path.join(os.path.dirname(__file__), "templates/content_page.html")
        self.response.out.write(template.render(path, add_base_values(template_values)))

class RPCHandler(webapp.RequestHandler):
    """ Allows the functions defined in the RPCMethods class to be RPCed."""
    def __init__(self):
        webapp.RequestHandler.__init__(self)
        self.getMethods = RPCGetMethods()
        self.postMethods = RPCPostMethods()

    def handle(self, action, handlers):
        func = None

        if action:
            if action[0] == '_':
                self.error(403) # access denied
                return
            else:
                func = getattr(handlers, action, None)

        if not func:
            self.error(404) # file not found
            return

        args = ()
        while True:
            key = 'arg%d' % len(args)
            val = self.request.get(key)
            if val:
                args += (simplejson.loads(val),)
            else:
                break

        result = func(self.request, *args)
        self.response.out.write(simplejson.dumps(result))

    def get(self, action):
        self.handle(action, self.getMethods)

    def post(self, action):
        self.handle(action, self.postMethods)
   

def _buildTransactionRow(community, transaction, fee_percentage, fee_minimum):
    """ Put together information for a single row in the maker activity table  """
    sale = {}
    cart = transaction.parent()
    sale['transaction'] = str(transaction.key())
    sale['transaction_status'] = transaction.status
    sale['when'] = transaction.when
    sale['date'] = str(cart.timestamp.replace(tzinfo=Utc_tzinfo()).astimezone(community.timeZone).date())
    sale['shipped'] = transaction.shipped        
    sale['shopper_name'] = cart.shopper_name
    sale['shopper_email'] = cart.shopper_email
    sale['shopper_phone'] = cart.shopper_phone
    sale['shopper_shipping'] = cart.shopper_shipping.encode('utf-8').replace("\n", "</br>")
    products = []
    sale_amount = 0.0
    sale_items = 0
    sale_shipping = 0.0
    
    for entry in transaction.detail:
        product = {}

        entry_fields = entry.split(':')
        if len(entry_fields) == 4:
            (product_key, items, amount, shipping) = entry_fields
        else:
            (product_key, items, amount) = entry_fields
            shipping = 0.0

        product_amount = float(amount)
        product_items = int(items)
        sale_items += product_items
        sale_amount += product_amount * product_items
        sale_shipping += float(shipping) * product_items
        product['product_name'] = Product.get(product_key).name
        product['items'] = product_items
        products.append(product)

    sale_fee = (sale_amount + sale_shipping) * fee_percentage + fee_minimum
    sale['products'] = products
    sale['items'] = sale_items
    sale['fee'] = "%.2f" % sale_fee
    sale['amount'] = "%.2f" % sale_amount
    sale['shipping'] = "%.2f" % sale_shipping
    sale['net'] = "%.2f" % ((sale_amount + sale_shipping) - sale_fee)

    return (sale, sale_items, sale_amount)


class RPCGetMethods:
    """ Defines the methods that can be RPCed.
    NOTE: Do not allow remote callers access to private/protected "_*" methods.
    """
    def GetShoppingCart(self, request, *args):
        """ Returns the items currently in the shopping cart. """
        session = get_current_session()
        results = {}
        items = session.get('ShoppingCartItems', [])
        delivery_option = session.get('DeliveryOption', "")
        products = []
        amount = 0.0
        for item in items:
            product = Product.get(item.product_key)
            if product:
                if delivery_option == 'local' and product.maker.handling_charge_for_pickup is False:
                    item.shipping = 0.0
                p = { "count": str(item.count),
                      "name": product.name,
                      "key": str(product.key()),
                      "image": str(product.image),
                      "price":'%3.2f' % item.price,
                      "shipping":'%3.2f' % item.shipping,
                      "total":'%3.2f' % item.subtotal,
                      "pickup_only": product.pickup_only
                      }
                products.append(p)
                amount += item.subtotal
            
        results = {'products':products, 'amount':"%.2f" % amount}
        return results

    def GetMakerActivityTable(self, request, *args):
        try:
            maker = Maker.get(args[0])
        except:
            return {"alert1":"Maker not found"}

        if not maker and not Authenticator.authorized_for(maker.user):
            self.error(403)
            return {"alert1":"You do not have permission to request that."}

        cursor = args[1]
        direction = args[2]
        q = db.Query(MakerTransaction)
        q.filter('maker =', maker.key())
        
        if cursor and cursor != '':
            if direction and direction == 'older':
                q.order('-when')
                q.filter('when <', cursor)
        else:
            q.order('-when')

        maker_transactions = q.fetch(15)
        sales = []
        total_sales = 0.0
        total_items = 0
        total_fees = 0.0
        total_net = 0.0
        community = Community.get_current_community()
        fee_percentage = (community.paypal_fee_percentage + community.fee_percentage)*0.01
        fee_minimum = community.paypal_fee_minimum + community.fee_minimum

        for transaction in maker_transactions:
            if transaction.status == 'Paid':
                (sale, sale_items, sale_amount) = _buildTransactionRow(community, transaction, fee_percentage, fee_minimum)
                total_items += sale_items
                total_sales += sale_amount
                sales.append(sale)

        sales.sort(key=lambda sale: sale['when'], reverse=True)

        return { 
            'sales':sales,
            'total_sales': "%.2f" % total_sales,
            'total_items':total_items
            }

    def GetScore(self, request, *args):
        community = Community.get_current_community()
        return {
            'makers':community.maker_score,
            'product':community.product_score,
            'pending':community.pending_score,
            }


class RPCPostMethods:
    """ Handle any RPC request that change the state of the sytem. """

    def AddProductToCart(self, request, *args):
        """ Add a product to the shopping cart by key. """
        results = {}
        product_id = args[0]
        try:
            product = Product.get(product_id)
        except:
            results["alert1"]="Product Not Found"
            return results
        if product.inventory < 1:
            results["alert1"]='No More ' + product.name + ' in stock'
            return results

        session = get_current_session()
        if not session.is_active():
            session.regenerate_id()
        items = session.get('ShoppingCartItems', [])

        for item in items:
            if item.product_key == product_id:
                if item.count + 1 > product.inventory:
                    results["alert1"]='No More ' + product.name + ' in stock'
                    return results
                else:
                    item.count += 1
                break
        else:
            newItem = ShoppingCartItem(product_key=product_id, shipping=product.shipping, price=product.actual_price, count=1)
            items.append(newItem)

        total = 0
        for item in items:
            total += item.count
        session['ShoppingCartItems'] = items
        count = str(total) + ' items'
        results["count"] = count 
        return results

    def RemoveProductFromCart(self, request, *args):
        """ Remove an item from the shopping cart by key """
        product_id = args[0]
        session = get_current_session()
        if not session.is_active():
            session.regenerate_id()
        items = session.get('ShoppingCartItems', [])
        
        for item in items:
            if item.product_key == product_id:
                if item.count > 1:
                    item.count -= 1
                else:
                    items.remove(item)
                break

        session['ShoppingCartItems'] = items
        return {"result":"success"}

    def RemoveAllProductFromCart(self, request, *args):
        """ Remove all of an item from the shopping cart by key """
        product_id = args[0]
        session = get_current_session()
        if not session.is_active():
            session.regenerate_id()
        items = session.get('ShoppingCartItems', [])

        for item in items:
            if item.product_key == product_id:
                items.remove(item)
                break

        session['ShoppingCartItems'] = items
        return {"result":"success"}

    def SetDeliveryOption(self, request, *args):
        """ Set local pickup or ship recalculate the cart as needed. """
        delivery_option = args[0];
        session = get_current_session()
        if not session.is_active():
            session.regenerate_id()
        session['DeliveryOption'] = delivery_option;
        return {"result":"success"};

    def SetMakerTransactionShipped(self, request, *args):
        try:
            maker = Maker.get(args[0])
        except:
            return {"alert1":"Maker not found"}
        
        if not maker and not Authenticator.authorized_for(maker.user):
            self.error(403)
            return {"alert1":"You do not have permission to request that."}

        try:
            transaction = MakerTransaction.get(args[1])
        except Exception, e:
            return {"alert1":"Transaction not found"}

        if not transaction:
            return {"alert1":"Transaction not found"}
        transaction.shipped = not transaction.shipped
        transaction.put()

        community = Community.get_current_community()
        fee_percentage = (community.paypal_fee_percentage + community.fee_percentage)*0.01
        fee_minimum = community.paypal_fee_minimum + community.fee_minimum
        
        (sale, additional_items, additional_sales) = _buildTransactionRow(community, transaction, fee_percentage, fee_minimum)
        return {"sale":sale}

    def OrderProductsInCart(self, request, *args):
        """ Deduct items from product inventory and create a CartTransaction
        and MakerTransactions to represent the cart. """    
        session = get_current_session()
        if not session.is_active():
            return{"message":"I don't see anything in your cart"}
        else:
            items = session.get('ShoppingCartItems', [])
            delivery_option = session.get('DeliveryOption', "")
            cart_transaction = CartTransaction(transaction_type='Sale')
            cart_transaction.shopper_name = sanitizeHtml(args[0])
            cart_transaction.shopper_email = sanitizeHtml(args[1])
            cart_transaction.shopper_phone = sanitizeHtml(args[2])
            shipping_info = sanitizeHtml(args[3].decode('unicode_escape'))

            logging.info(cart_transaction.shopper_name + " : " +cart_transaction.shopper_email + " : " + shipping_info)

            cart_transaction.shopper_shipping = shipping_info
            cart_transaction.put()

            maker_transactions = []
            products = []
            maker_business_ids = []
            adjusted_items = []
            for item in items:
                product = Product.get(item.product_key)
                if product.inventory - item.count < 0:
                    return{"alert1":"%d %s in stock, but %d in your cart - please remove %d" 
                           % (product.inventory, product.name, item.count, item.count - product.inventory) }
                else:
                    product.sold = item.count

                products.append(product)

                if delivery_option == 'local' and product.maker.handling_charge_for_pickup is False:
                    item.shipping = 0.0

                for maker_transaction in maker_transactions:
                    if maker_transaction.maker.key() == product.maker.key():

                        entry = "%s:%s:%s:%s" % (str(product.key()),
                                              str(item.count),
                                              str(item.price),
                                              str(item.shipping))
                        maker_transaction.detail.append(entry)
                        break
                    else:
                        logging.info(str(maker_transaction.maker.key()) + "!=" + str(product.maker.key()))
                else:
                    when = "%s|%s" % (datetime.now(), hashlib.md5(str(product.maker.key())+get_current_session().sid).hexdigest())
                    maker_transaction = MakerTransaction(parent=cart_transaction,
                                                         maker=product.maker,
                                                         email=product.maker.paypal_business_account_email,
                                                         when=when)

                    entry = "%s:%s:%s:%s" % (str(product.key()),
                                          str(item.count),
                                          str(item.price),
                                          str(item.shipping))
                    maker_transaction.detail.append(entry)
                    maker_transactions.append(maker_transaction)
                    maker_business_ids.append((product.maker.paypal_business_account_email, 1.00))

                adjusted_items.append(item)

            community = Community.get_current_community()
            base_url = request.url.replace(request.path, '')

            receivers = ShoppingCartItem.createReceiverList(community=community,
                                                            shopping_cart_items=adjusted_items)

            try:
                if community.use_sandbox:
                    action_url='https://svcs.sandbox.paypal.com/AdaptivePayments/Pay'
                else:
                    action_url='https://svcs.paypal.com/AdaptivePayments/Pay'

                payment = PaypalChainedPayment( 
                    primary_recipient=receivers['primary'],
                    additional_recipients=receivers['others'],
                    api_username=community.api_username,
                    api_password=community.api_password,
                    api_signature=community.api_signature,
                    application_id=community.application_id,
                    client_ip=request.remote_addr,
                    cancel_url=base_url+'/cancel?payKey=${payKey}',
                    return_url=base_url+'/return?payKey=${payKey}',
                    action_url = action_url,
                    ipn_url=base_url+'/ipn',
                    sandbox_email=community.paypal_email_address,
                    )
            except TooManyRecipientsException:
                cart_transaction.delete()
                return {"message":"Paypal allows no more than five different Makers' products in a cart. Please divide your purchase."}
            try:
                response = payment.execute()
                paypalPaymentResponse = PaypalPaymentResponse( parent=cart_transaction, response=response.content)
                paypalPaymentResponse.put();
                confirmation_url = payment.buildRedirectURL(response=response, sandbox=community.use_sandbox)
            except Exception, e:
                logging.error('Exception handling Paypal transaction: %s',  str(e));
                response = None

            if response and confirmation_url:
                cart_transaction.transaction_status = 'CREATED';
                cart_transaction.paypal_pay_key = payment.pay_key
                cart_transaction.put()
                db.put(maker_transactions)
                session.pop('ShoppingCartItems')
                community.increment_pending_score()
                return {"redirect":"%s" % confirmation_url} 
            else:
                logging.error("A Paypal checkout failed! Here's the cart: " + str(items))
                cart_transaction.transaction_status = 'ERROR'
                cart_transaction.error_details = 'Error Talking to Paypal.'
                cart_transaction.put()
                # TBD Generate email alert?
                return{"message":"An error occured talking to Paypal. Please try again later. You can also call us or email. We have logged the error and will be looking into it right away. Your account has not been charged."}

    def SetApprovalStatus(self, request, *args):
        """ Change the approval status of a  maker. """
        if not users.is_current_user_admin():
            self.error(403)
            return {"alert1":"You do not have permission to do that."}

        try:
            maker = Maker.get(args[0])
        except:
            return {"alert1":"Maker not found."}
        if maker:
            status = args[1]
            maker.approval_status = status
            maker.put()
            return{"key":str(maker.key()), "approval_status":status}
        else:
            logging.error("Attempt to change approval status of a maker which doesn't exist: %s\n", maker_id)
            self.error(404)

    def EditContent(self, request, *args):
        """ Change content for a content page. """
        if not users.is_current_user_admin():
            self.error(403)
            return{"alert1":"You do not have permission to edit that."}
        else:
            name = args[0]
            page = Page.get_or_insert(name, name=name)
            page.content=args[1].replace(u'\u201c', '"').replace(u'\u201d', '"').decode('unicode_escape')
            page.put()

class UploadImage(webapp.RequestHandler):
    """ Handle temporary image uploads."""
    def post(self):
        photo_file = self.request.get("img")
        parent_form = self.request.get("parent_form")
        max_width = int(self.request.get("max_width"))
        max_height = int(self.request.get("max_height"))
        image_field = self.request.get("image_field")
        preview = self.request.get("preview")
        error = self.request.get("error")
        photo_is_valid = photo_file is not None and photo_file != ''
        photo_is_valid = photo_is_valid and len(photo_file) < 1024*1024
        output = """<script language="JavaScript" type="text/javascript">
                     var parDoc = window.parent.document;
                     var picture_error = parDoc.getElementById("%(error)s");
                     var picture_preview = parDoc.getElementById("%(preview)s"); """ % {'preview':preview, 'error':error}
        if photo_is_valid:
            try:
                photo = images.resize(photo_file, max_width, max_height)
            except:
                photo = None;

            if photo:
                image = Image( 
                    category='Temporary',
                    content=photo,
                    )
                image.put()
                output += """ picture_error.innerHTML = ""; """
                output += """ hidden_element = parDoc.getElementById("%(image_field)s");
                              if(!hidden_element) {
                                parent_form = parDoc.getElementById("%(parent_form)s");
                                var hidden_element = document.createElement("input");
                                hidden_element.type="hidden";
                                hidden_element.name="%(image_field)s";
                                hidden_element.id="%(image_field)s";
                                parent_form.appendChild(hidden_element); 
                              }
                              hidden_element.value="%(image_key)s";
                          """ % {'image_field':image_field, 'parent_form':parent_form, 'image_key':str(image.key())}
                output += """ picture_preview.innerHTML = "<img src='/images/%s' id='preview_picture_tag' \>"; """ % (str(image.key()))
            else:
                output += """ picture_error.innerHTML = "Resize failed."; picture_preview.innerHTML = '';""";
        else:
            output += """  picture_error.innerHTML = "Not a valid image."; picture_preview.innerHTML = '';""";
        
        output += "</script>"
        self.response.out.write(output)


class DisplayImage(webapp.RequestHandler):
    def get(self, image_id):
        if image_id == 'None':
            image = None;
        else:
            try:
                image = db.get(image_id)
            except:
                image = None

        self.response.headers['Content-Type'] = "image/png"
        self.response.headers['Cache-Control'] = "max-age=2592000, must-revalidate"

        if image and image.content:
            self.response.out.write(image.content)
        else:
            self.response.out.write(png_image_white_pixel)

class ProductSearch(webapp.RequestHandler):
    def get(self):
        template_values = {
            'title':'Search Results',
            'products':Product.searchByTag(self.request.get('search')),
            }

        path = os.path.join(os.path.dirname(__file__), "templates/catalog.html")
        self.response.out.write(template.render(path, add_base_values(template_values)))

class CategorySearch(webapp.RequestHandler):
    def get(self):
        category = self.request.get('category')

        if(category):
            category = urllib.unquote(category)

        number_to_return = 9;
        where_to_start = 0
        start = self.request.get('start')
        if start:
            try:
                where_to_start = int(start)
            except:                
                return
        products = Product.findProductsByCategory(category, number_to_return, where_to_start)

        next = 0
        num_products = len(products)
        if num_products >= number_to_return:
            next = where_to_start + num_products
        if num_products == number_to_return:
            products.pop()

        previous = 0
        show_previous = False
        if where_to_start >= number_to_return:
            show_previous = True
            previous = where_to_start - number_to_return

        template_values = {
            'title':'Search Results',
            'category':category,
            'products':products,
            'next':next,
            'show_previous':show_previous,
            'previous':previous,
            }

        path = os.path.join(os.path.dirname(__file__), "templates/catalog.html")
        self.response.out.write(template.render(path, add_base_values(template_values)))

class MakerDirectory(webapp.RequestHandler):
    def get(self):
        makers = Maker.all()
        makers.filter('approval_status =', 'Approved')
        makers.filter('accepted_terms =', True)
        makers.order('joined')
        template_values = {
            'title':'Maker Directory',
            'stores':makers,
            }

        path = os.path.join(os.path.dirname(__file__), "templates/maker_directory.html")
        self.response.out.write(template.render(path, add_base_values(template_values)))

class AboutPage(webapp.RequestHandler):
    def get(self):
        community = Community.get_current_community()
        makers = Maker.all().filter('approval_status =', 'Approved')
        template_values = {
            'community':community,
            'makers':makers,
            'title':'About Us',
            }

        path = os.path.join(os.path.dirname(__file__), "templates/about.html")
        self.response.out.write(template.render(path, add_base_values(template_values)))

def main():
    app = webapp.WSGIApplication([
        (r'/rpc/(GetShoppingCart)', RPCHandler),
        (r'/rpc/(GetMakerActivityTable)', RPCHandler),
        (r'/rpc/(SetApprovalStatus)', RPCHandler),
        (r'/rpc/(AddProductToCart)', RPCHandler),
        (r'/rpc/(RemoveProductFromCart)', RPCHandler),
        (r'/rpc/(RemoveAllProductFromCart)', RPCHandler),
        (r'/rpc/(SetMakerTransactionShipped)', RPCHandler),
        (r'/rpc/(OrderProductsInCart)', RPCHandler),
        (r'/rpc/(EditContent)', RPCHandler),
        (r'/rpc/(GetScore)', RPCHandler),
        (r'/rpc/(SetDeliveryOption)', RPCHandler),
        ('/', CommunityHomePage),
        ('/communities', SiteHomePage),
        ('/maker', MakerPage),
        ('/maker/add', MakerPage),
        (r'/maker/edit/(.*)', EditMakerPage),
        ('/maker/edit', EditMakerPage),
        ('/product/add', ProductPage),
        (r'/product/edit/(.*)/(.*)', EditProductPage),
        (r'/product/(.*)/(.*)', ViewProductPage),
        ('/login', Login),
        ('/logout', Logout),
        ('/makers', ListMakers),
        (r'/maker_store/(.*)', MakerStorePage),
        (r'/maker_dashboard/(.*)', MakerDashboard),
        ('/community/add', CommunityPage),
        ('/community/edit', EditCommunityPage),
        ('/checkout', CheckoutPage),
        ('/news_items', ListNewsItems),
        ('/news_item/add', AddNewsItem),
        (r'/news_item/edit/(.*)', EditNewsItem),
        (r'/news_item/(.*)', ViewNewsItem),
        ('/advertisement/add', AdvertisementPage),
        (r'/advertisement/edit/(.*)', EditAdvertisementPage),
        (r'/advertisement/(.*)', ViewAdvertisementPage),
        (r'/(join)', RenderContentPage),
        (r'/(privacy)', RenderContentPage),
        (r'/(terms)', RenderContentPage),
        ('/about', AboutPage),
        ('/advertisements', ListAdvertisements),
        ('/return', CompletePurchase),
        ('/cancel', CompletePurchase),
        (r'/images/(.*)', DisplayImage),
        ('/image/upload', UploadImage),
        ('/search', ProductSearch),
        ('/category', CategorySearch),
        ('/maker_directory', MakerDirectory),
        (r'.*', NotFoundErrorHandler)
        ], debug=True)
    util.run_wsgi_app(app)

if __name__ == '__main__':
    main()
