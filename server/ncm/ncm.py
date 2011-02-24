# !/usr/bin/env python
import os
import logging
from google.appengine.api import images

import urllib
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp import util
from google.appengine.api import users
from google.appengine.ext import db
from google.appengine.ext.db import djangoforms

from gaesessions import get_current_session

from model import *
from forms import *
from payment import *
from authentication import Authenticator

class MakerPage(webapp.RequestHandler):
    """ A page for adding a Maker  """
    def get(self):
        authenticator = Authenticator(self)

        try:
            (user, maker) = authenticator.authenticate()
        except:
            # Return immediately
            return

        if user and maker:
            self.redirect('/maker_dashboard/' + str(maker.key()))
            return
        else:
            data = MakerForm()
            template_values = { 'title':'Open Your Store',
                                'new':True,
                                'form':data,
                                'uri':self.request.uri}
            path = os.path.join(os.path.dirname(__file__), "templates/maker.html")
            logging.info("Showing Registration Page")
            self.response.out.write(template.render(path, template_values))

    def post(self):
        session = get_current_session()
        community = Community.get_community_for_slug(session.get('community'))
        
        if not community:
            self.error(404)
            self.response.out.write("I don't recognize that community")
            return

        data = MakerForm(data=self.request.POST)
        terms_accepted = self.request.get('term1') and self.request.get('term2') and self.request.get('term2')

        if data.is_valid() and terms_accepted:
            # Save the data, and redirect to the view page
            entity = data.save(commit=False)
            entity.user = users.get_current_user()
            entity.community = community
            entity.put()
            logging.info('User: ' + str(entity.user) + ' has joined ' + entity.community.name)
            self.redirect('/community/' + community.slug)
        else:
            if not terms_accepted:
                errors = ['You must accept the terms and conditions to use this site.']

            # Reprint the form
            template_values = { 'title':'Open Your Store', 
                                'extraErrors':errors,
                                'form' : data, 
                                'uri': self.request.uri}
            path = os.path.join(os.path.dirname(__file__), "templates/maker.html")
            logging.info("Showing Registration Page")
            self.response.out.write(template.render(path, template_values))

class EditMakerPage(webapp.RequestHandler):
    """ Edit a Maker store """
    def get(self, id):
        if not id:
            logging.info('No id found for EditMakerPage')
            maker = Authenticator.getMakerForUser(users.get_current_user())
            if maker:
                id = maker.key()
            else:
                self.error(404)
                self.response.out.write("I don't recognize that maker.")
                return
        else:
            try:
                maker = Maker.get(id)
            except:
                self.error(404)
                self.response.out.write("I don't recognize that maker.")
                return                

        if maker and Authenticator.authorized_for(maker.user):
            template_values = { 'form' : MakerForm(instance=maker), 'id' : id, 
                                'uri':self.request.uri, 'maker':maker,
                                'community':maker.community,
                                'title':'Update Store Information'}
            path = os.path.join(os.path.dirname(__file__), "templates/maker.html")
            self.response.out.write(template.render(path, template_values))
        else:
            self.redirect('/maker/add')

    def post(self, id):        
        session = get_current_session()
        community = Community.get_community_for_slug(session.get('community'))
        
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
            if data.is_valid():
                # Save the data, and redirect to the view page
                entity = data.save(commit=False)
                entity.user = users.get_current_user()
                entity.put()
                self.redirect('/community/' + community.slug)
            else:
                # Reprint the form
                template_values = { 'form' : ProductForm(instance=maker), 'id' : id, 'uri':self.request.uri}
                path = os.path.join(os.path.dirname(__file__), "templates/maker.html")
                self.response.out.write(template.render(path, template_values))

class ProductPage(webapp.RequestHandler):
    """ Add a Product """
    def buildImageUploadForm(self):
        return """
            <div><label>Product Image:</label></div>
            <div><input type="file" name="img"/></div> """

    def get(self):
        authenticator = Authenticator(self)

        try:
            (user, maker) = authenticator.authenticate()
        except:
            # Return immediately
            return

        if not user or not maker:
            self.redirect('/')
            return
        else:
            template_values = { 'form' : ProductForm(), 'maker':maker, 
                                'upload_form': self.buildImageUploadForm(), 
                                'uri':self.request.uri}
            path = os.path.join(os.path.dirname(__file__), "templates/product.html")
            self.response.out.write(template.render(path, template_values))

    def post(self):
        authenticator = Authenticator(self)

        try:
            (user, maker) = authenticator.authenticate()
        except:
            # Return immediately
            return

        if not user or not maker:
            self.redirect('/')
            return
        else:
            data = ProductForm(data=self.request.POST)
            if data.is_valid():
                entity = data.save(commit=False)
                entity.maker = maker
                entity.put()
                upload = ProductImage()
                try:
                    upload.product = entity
                    upload.image = images.resize(self.request.get("img"), 240, 240)
                    upload.put()
                except images.NotImageError:
                    pass
                    # Have to come up with a much better way of handling this
                    # self.redirect('/')
                self.redirect('/maker_dashboard/' + str(maker.key()))
            else:
                # Reprint the form
                template_values = { 'form' : data, 'maker':maker,
                                    'upload_form': self.buildImageUploadForm(),
                                    'uri':self.request.uri}
                path = os.path.join(os.path.dirname(__file__), "templates/product.html")
                self.response.out.write(template.render(path, template_values))

class UploadProductImage(webapp.RequestHandler):
    def post(self):
        upload = ProductImage()
        bits = self.request.get("img")
        try:
            upload.image = images.resize(self.request.get("img"), 240, 240)
            upload.put()
            self.redirect('/product_images/'+str(upload.key()))
        except images.NotImageError:
            # Have to come up with a much better way of handling this
            self.redirect('/')

class DisplayImage(webapp.RequestHandler):
    def get(self, image_id):
        productImage = db.get(image_id)
        if productImage.image:
            self.response.headers['Content-Type'] = "image/png"
            self.response.out.write(productImage.image)
        else:
            self.error(404)

class EditProductPage(webapp.RequestHandler):
    """ Edit an existing Product """

    def buildImageUploadForm(self, ):
        return """
            <div><label>Product Image:</label></div>
            <div><input type="file" name="img"/></div> """

    def get(self, id):
        authenticator = Authenticator(self)

        try:
            (user, maker) = authenticator.authenticate()
        except:
            # Return immediately
            return

        if not maker:
            session = get_current_session()
            community = Community.get_community_for_slug(session.get('community'))
        
            if not community:
                self.error(404)
                self.response.out.write("I don't recognize that community.")
                return

            self.redirect('/community/' + community.slug)
            return
        else:
            product = Product.get(id)

            if str(product.maker.key()) != str(maker.key()):
                self.error(403)
                self.response.out.write("You do not have permission to edit that product.")
                return
                
            template_values = { 'form' : ProductForm(instance=product), 
                                'maker' : maker, 
                                'upload_form': self.buildImageUploadForm(),
                                'product':product, 'id' : id, 
                                'uri':self.request.uri}
            path = os.path.join(os.path.dirname(__file__), "templates/product.html")
            self.response.out.write(template.render(path, template_values))

    def post(self, id):
      id = self.request.get('_id')      
      product = Product.get(id)
      authenticator = Authenticator(self)

      try:
          (user, maker) = authenticator.authenticate()
      except:
          # Return immediately
          return

      if not maker or maker.key() != product.maker.key():
          if maker and product.maker:
              logging.error('Illegal attempt to edit product owned by: ' + product.maker.full_name + ' by ' + maker.full_name + '(' + str(maker.key()) + ' != ' + str(product.maker.key()) + ')')
          else:
              logging.error('Illegal attempt to edit product owned by: ' + product.maker.full_name + ' by unauthenticated guest')
          self.redirect('/')
          return
      else:
          data = ProductForm(data=self.request.POST, instance=product)
          if data.is_valid():
              entity = data.save(commit=False)
              entity.put()
              image = self.request.get("img")
              if image:
                  upload = ProductImage(parent=entity)
                  for product_image in entity.product_images:
                      product_image.delete()
                  try:
                      upload.product = entity
                      upload.image = images.resize(image, 240, 240)
                      upload.put()
                  except images.NotImageError:
                      pass
              self.redirect('/maker_dashboard/' + str(maker.key()))
          else:
              # Reprint the form
              template_values = { 'form' : ProductForm(instance=product), 
                                  'maker' : maker,
                                  'id' : id, 'uri':self.request.uri}
              path = os.path.join(os.path.dirname(__file__), "templates/product.html")
              self.response.out.write(template.render(path, template_values))

class Login(webapp.RequestHandler):
    """ Just authenticates then redirects to the home page """
    def get(self, community_slug):
        authenticator = Authenticator(self)

        try:
            (user, maker) = authenticator.authenticate()
        except:
            # Return immediately
            return

        session = get_current_session()
        session['community'] = community_slug
        # session.start(ssl_only=True)
        session.regenerate_id()

        if maker:
            self.redirect('/maker_dashboard/%s' % str(maker.key()) )
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
        self.redirect(users.create_logout_url('/community/'+ community))

class CommunityHomePage(webapp.RequestHandler):
    """ Renders the home page template. """
    def get(self, community_slug):
        session = get_current_session()

        community = Community.get_current_community(community_slug, session)

        if not community:
            self.error(404)
            self.response.out.write("I don't recognize that community.")
            return

        session['community'] = community.slug

        user = users.get_current_user()
        maker = None
        if user is not None:
            maker = Authenticator.getMakerForUser(user)

        stuff = Product.all()
        products = []
        for product in stuff:
            if str(product.maker.community.key()) == str(community.key()):
                products.append(product)

        template_values = { 'title': community.name, 
                            'community':community,
                            'products':products, 'maker':maker}

        items = session.get('ShoppingCartItems', [])
        count = 0
        if items != ():
            for item in items:
                count += item.count

        template_values['cartItems'] = count
        
        path = os.path.join(os.path.dirname(__file__), "templates/home.html")
        self.response.out.write(template.render(path, template_values))

class PrivacyPage(webapp.RequestHandler):
    """ Renders a store page for a particular maker. """
    def get(self):
        template_values = { 'title':'Privacy Policy'}
        path = os.path.join(os.path.dirname(__file__), "templates/privacy.html")
        self.response.out.write(template.render(path, template_values))

class TermsPage(webapp.RequestHandler):
    """ Renders the terms and conditions page. """
    def get(self):
        template_values = { 'title':'Terms and Conditions'}
        path = os.path.join(os.path.dirname(__file__), "templates/terms.html")
        self.response.out.write(template.render(path, template_values))

class MakerDashboard(webapp.RequestHandler):
    """ Renders a page for Makers to view and manage their catalog and sales """
    def get(self, maker_id):
        authenticator = Authenticator(self)

        try:
            (user, maker) = authenticator.authenticate()
        except:
            # Return immediately
            return

        if not maker or not str(maker.key()) == maker_id:
            logging.info('=== MakerDashboard.get(): ' + str(maker.key()) + ' does not equal ' + maker_id)
            self.redirect("/maker_store/" + maker_id)            
            return
        else:
            q = MakerTransaction.gql("WHERE maker = :1", maker.key())
            maker_transactions = q.fetch(60)
            sales = []
            class Sale:
                pass
            total_sales = 0.0
            total_items = 0
            for transaction in maker_transactions:
                for entry in transaction.detail:
                    sale = Sale()                
                    (product_key, items, amount) = entry.split(':')
                    sale.product = Product.get(product_key).name
                    sale.items = int(items)
                    sale.amount = float(amount)
                    sales.append(sale)
                    total_items += sale.items
                    total_sales += sale.amount * sale.items

                    
            template_values = { 'title':'Maker Dashboard',
                                'community':maker.community, 
                                'sales':sales,
                                'maker':maker,
                                'total_sales':total_sales,
                                'total_items':total_items}
            path = os.path.join(os.path.dirname(__file__), "templates/maker_dashboard.html")
            self.response.out.write(template.render(path, template_values))

class MakerStorePage(webapp.RequestHandler):
    """ Renders a store page for a particular maker. """
    def get(self, maker_id):
        maker = Maker.get(maker_id)
        template_values = { 'maker':maker}
        path = os.path.join(os.path.dirname(__file__), "templates/maker_store.html")
        self.response.out.write(template.render(path, template_values))

class AddProductToCart(webapp.RequestHandler):
    """ Accept a JSON RPC request to add a product to the cart"""
    def post(self):
        logging.info('AddProductToCart: ' + str(self.request))
        product_id = self.request.get('arg0')
        session = get_current_session()
        if not session.is_active():
            # session.start(ssl_only=True)
            session.regenerate_id()
        items = session.get('ShoppingCartItems', [])

        for item in items:
            if item.product == product_id:
                item.count += 1
                break
        else:
            newItem = ShoppingCartItem(product=product_id, count=1)
            logging.info('New item: ' + str(newItem.product))
            items.append(newItem)

        total = 0
        for item in items:
            total += item.count
        session['ShoppingCartItems'] = items
        count = str(total) + ' items'
        self.response.out.write("{ \"count\":\"" + count + "\"}")

class RemoveProductFromCart(webapp.RequestHandler):
    """ Accept a JSON RPC request to remove a product from the cart"""
    def get(self):
        pass

    def post(self):
        product_id = self.request.get('arg0')
        session = get_current_session()
        if not session.is_active():
            # session.start(ssl_only=True)
            session.regenerate_id()
        items = session.get('ShoppingCartItems', [])

        for item in items:
            if item.product == product_id:
                if item.count > 1:
                    item.count -= 1
                else:
                    items.remove(item)
                break

        session['ShoppingCartItems'] = items
        self.response.out.write('{"result":"success"}')

class GetOrderNowButton(webapp.RequestHandler):
    """ Accept a JSON RPC request to provide information for a paypal payment button"""
    def get(self):
        session = get_current_session()
        if not session.is_active():
            self.response.out.write('{"button_available":"false"}')
        else:
            community = Community.get_community_for_slug(session.get('community'))
            if community.use_sandbox:
                email = community.paypal_sandbox_email_address
                action_url = 'https://www.sandbox.paypal.com/cgi-bin/webscr'
            else:
                email = community.paypal_email_address
                action_url = 'https://www.paypal.com/cgi-bin/webscr'
            item_name = 'Shopping Cart'
            item_number = '123'
            items = session.get('ShoppingCartItems', [])
            return_url = 'http://nevadacountymakes.com/return'
            cancel_url = 'http://nevadacountymakes.com/cancel'
            transaction_id = 'abc'
            
            message = '{'
            message += '"products":['
            amount = 0.0
            for item in items:
                product = Product.get(item.product)
                if product:
                    message += '{"count":"' + str(item.count) + '",'
                    message += '"name":"' + product.name + '",'
                    message += '"key":"' + str(product.key()) + '",'
                    message += '"total":"' + '%3.2f' % (product.price * item.count)+ '"},'
                    amount += (product.price * item.count)
            message += ']'
            message += ',"amount":"' + '%3.2f' % amount + '"'
            message += ',"button_available":"true"'
            message += ',"action_url":"' + action_url + '"'
            message += ',"email":"' + email + '"'
            message += ',"item_name":"' + item_name + '"'
            message += ',"item_number":"' + item_number + '"'
            message += ',"return_url":"' + return_url + '"'
            message += ',"cancel_url":"' + cancel_url + '"'
            message += ',"transaction_id":"' + transaction_id + '"'
            message += '}'

            self.response.out.write(message)

    def post(self):
        pass

class EditCommunityPage(webapp.RequestHandler):
    """ A page for managing community info  """
    def get(self):
        authenticator = Authenticator(self)

        try:
            (user, maker) = authenticator.authenticate()
        except:
            self.error(500)
            self.response.out.write("Error identifying user.")            
            # Return immediately
            return

        if user and users.is_current_user_admin():
            community = Community.get_community_for_slug(get_current_session().get('community'))
        
            if not community:
                self.error(404)
                self.response.out.write("I don't recognize that community")
                return

            data = CommunityForm(instance=community)
            template_values = { 'title':'Create a Community',
                                'form':data, 'id':community.key(),
                                 'uri':self.request.uri}
            path = os.path.join(os.path.dirname(__file__), "templates/community.html")
            self.response.out.write(template.render(path, template_values))

        else:
            self.error(403)
            self.response.out.write('You do not have permission to edit this community.')
            
    def post(self):
        authenticator = Authenticator(self)
            
        try:
            (user, maker) = authenticator.authenticate()
        except:
            self.error(500)
            self.response.out.write("Error identifying user.")            
            # Return immediately
            return

        if user and users.is_current_user_admin():
            id = self.request.get('_id')
            community = Community.get(id)
            data = CommunityForm(data=self.request.POST, instance=community)
            if data.is_valid():
                # Save the data, and redirect to the view page
                entity = data.save(commit=False)
                entity.slug = Community.get_slug_for_name(entity.name)
                entity.put()
                self.redirect('/community/' + entity.slug)
            else:
                # Reprint the form
                template_values = { 'title':'Create a Community', 
                                    'id' : id,
                                    'form' : data, 
                                    'uri': self.request.uri}
                path = os.path.join(os.path.dirname(__file__), "templates/community.html")
                self.response.out.write(template.render(path, template_values))
        else:
            self.error(403)
            self.response.out.write('You do not have permission to edit this community.')

class AddCommunityPage(webapp.RequestHandler):
    """ A page for adding a Community  """
    def get(self):
        authenticator = Authenticator(self)

        try:
            (user, maker) = authenticator.authenticate()
        except:
            # Return immediately
            return

        if user and users.is_current_user_admin():
            data = CommunityForm()
            template_values = { 'title':'Create a Community',
                                'form':data, 
                                'uri':self.request.uri}
            path = os.path.join(os.path.dirname(__file__), "templates/community.html")
            self.response.out.write(template.render(path, template_values))

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
        data = CommunityForm(data=self.request.POST)
        if data.is_valid():
            # Save the data, and redirect to the view page
            entity = data.save(commit=False)
            entity.slug = Community.get_slug_for_name(entity.name)
            entity.put()
            self.redirect('/community/' + entity.slug)
        else:
            # Reprint the form
            template_values = { 'title':'Create a Community', 
                                'form' : data, 
                                'uri': self.request.uri}
            path = os.path.join(os.path.dirname(__file__), "templates/community.html")
            self.response.out.write(template.render(path, template_values))

class SiteHomePage(webapp.RequestHandler):
    """ A site root page """
    def get(self):
        communities = Community.all()
        message = '<h2>Please visit one of our communities</h2>'
        for community in communities:
            message += '<p><a href="%s">%s</a></p>' % ('/community/'+community.slug,community.name)
        self.response.out.write(message)

class CheckoutPage(webapp.RequestHandler):
    def get(self):
        session = get_current_session()
        if not session.is_active():
            self.response.out.write("I don't see anything in your cart")
            return
        else:
            community = Community.get_community_for_slug(session.get('community'))        
            if not community:
                self.error(404)
                self.response.out.write("I don't recognize that community")
                return

            items = session.get('ShoppingCartItems', [])
            products = []
            for item in items:
                product = Product.get(item.product)
                if product:
                    product.count = item.count
                    product.total = '%3.2f' % (product.price * product.count)
                    products.append(product)
            template_values = { 'title':'Checkout',
                                'products':products,
                                'community':community,
                                'uri':self.request.uri}
            path = os.path.join(os.path.dirname(__file__), "templates/checkout.html")
            self.response.out.write(template.render(path, template_values))
            
    def post(self):
        pass

class NotFoundErrorHandler(webapp.RequestHandler):
    """ A site root page """
    def get(self):
        self.error(404)
        self.response.out.write("Opps, that doesn't seem to be a valid page.")

class OrderProductsInCart(webapp.RequestHandler):
    """ Deduct items from product inventory and create a CartTransaction
    and MakerTransactions to represent the cart. TBD: inventory changes should be
    protected by transactions to ensure integrity! """

    def get(self):
        """ Ignore gets. This isn't an idempotent operation. """
        pass

    def post(self):
        session = get_current_session()
        if not session.is_active():
            self.response.out.write("{ \"message\":\"" 
                                    + "I don't see anything in your cart"
                                    + "\"}")
            return
        else:
            items = session.get('ShoppingCartItems', [])
            cart_transaction = CartTransaction(transaction_type='Sale')
            cart_transaction.put()

            maker_transactions = []
            products = []
            for item in items:
                product = Product.get(item.product)
                if product.inventory > 0:
                    product.inventory -= item.count
                products.append(product)
                for maker_transaction in maker_transactions:
                    if maker_transaction.maker.key() == product.maker.key():
                        entry = "%s:%s:%s" % (str(product.key()), 
                                              str(item.count), 
                                              str(product.price))
                        maker_transaction.detail.append(entry)
                        break
                    else:
                        logging.info(str(maker_transaction.maker.key()) + "!=" + str(product.maker.key()))
                else:
                    maker_transaction = MakerTransaction(parent=cart_transaction,
                                                         maker=product.maker)
                    entry = "%s:%s:%s" % (str(product.key()), 
                                          str(item.count), 
                                          str(product.price))
                    maker_transaction.detail.append(entry)
                    maker_transactions.append(maker_transaction)

            db.put(maker_transactions)
            db.put(products)

            self.response.out.write("{ \"message\":\"" 
                                    + "Thank you for your order."
                                    + "\"}")
            session.pop('ShoppingCartItems')
            return

class ListNewsItems(webapp.RequestHandler):
    """ Add a new news item. """
    def get(self):
        session = get_current_session()
        community = Community.get_community_for_slug(session.get('community'))
        
        if not community:
            self.error(404)
            self.response.out.write("I don't recognize that community")
            return

        q = db.Query(NewsItem)

        q.filter('show =', True).filter('community =', community)
        news_items = q.fetch(limit=50)
        logging.info('items :' + str(news_items))
        template_values = { 'title':'News Items', 'news_items': news_items}
        path = os.path.join(os.path.dirname(__file__), "templates/news_items.html")
        self.response.out.write(template.render(path, template_values))


class ViewNewsItem(webapp.RequestHandler):
    """ View an existing item. """
    def get(self, slug):
        authenticator = Authenticator(self)
        try:
            (user, maker) = authenticator.authenticate()
        except:
            # Return immediately
            return

        if user: # Need to authorize community coordinators
            news_item = NewsItem.get_news_item_for_slug(slug)
            q = NewsItem.all()
            q.filter('show =', True)
            news_items = q.fetch(limit=3)
            template_values = { 'title':'News',
                                'news_item':news_item, 
                                'news_items':news_items,
                                'uri':self.request.uri}
            path = os.path.join(os.path.dirname(__file__), "templates/news_item.html")
            self.response.out.write(template.render(path, template_values))

        else:
            self.error(403)
            self.response.out.write('You do not have permission to create a new news item for this community.')


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
            self.response.out.write(template.render(path, template_values))

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
            self.redirect('/news_items')
        else:
            # Reprint the form
            template_values = { 'title':'Create a NewsItem', 
                                'form' : data, 
                                'id': id,
                                'uri': self.request.uri}
            path = os.path.join(os.path.dirname(__file__), "templates/news_item.html")
            self.response.out.write(template.render(path, template_values))

class AddNewsItem(webapp.RequestHandler):
    """ Add a new news item. """
    def get(self):
        authenticator = Authenticator(self)
        try:
            (user, maker) = authenticator.authenticate()
        except:
            # Return immediately
            return

        if user: # Need to authorize community coordinators
            data = NewsItemForm()
            template_values = { 'title':'Create a News Item',
                                'form':data, 
                                'uri':self.request.uri}
            path = os.path.join(os.path.dirname(__file__), "templates/news_item.html")
            self.response.out.write(template.render(path, template_values))

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
            community = Community.get_community_for_slug(session.get('community'))
        
            if not community:
                self.error(404)
                self.response.out.write("I don't recognize that community")
                return
            entity.community = community
            entity.slug = NewsItem.get_slug_for_title(entity.title)
            entity.put()
            self.redirect('/news_items')
        else:
            # Reprint the form
            template_values = { 'title':'Create a NewsItem', 
                                'form' : data, 
                                'id' : id,
                                'uri': self.request.uri}
            path = os.path.join(os.path.dirname(__file__), "templates/news_items.html")
            self.response.out.write(template.render(path, template_values))

def main():
    app = webapp.WSGIApplication([
        ('/', SiteHomePage),
        ('/communities', SiteHomePage),
        ('/maker', MakerPage),
        ('/maker/add', MakerPage),
        (r'/maker/edit/(.*)', EditMakerPage),
        ('/maker/edit', EditMakerPage),
        ('/product/add', ProductPage),
        (r'/product/edit/(.*)', EditProductPage),
        ('/product/edit', EditProductPage),
        ('/privacy', PrivacyPage),
        ('/terms', TermsPage),
        (r'/community/(.*)/login', Login),
        ('/logout', Logout),
        (r'/maker_store/(.*)', MakerStorePage),
        (r'/maker_dashboard/(.*)', MakerDashboard),
        (r'/product_images/(.*)', DisplayImage),
        ('/upload_product_image', UploadProductImage), 
        ('/AddProductToCart', AddProductToCart),
        ('/RemoveProductFromCart', RemoveProductFromCart),
        ('/GetOrderNowButton', GetOrderNowButton),
        ('/community/add', AddCommunityPage),
        ('/community/edit', EditCommunityPage),
        (r'/community/(.*)', CommunityHomePage),
        ('/checkout', CheckoutPage),
        ('/OrderProductsInCart', OrderProductsInCart),
        ('/news_items', ListNewsItems),
        ('/news_item/add', AddNewsItem),
        (r'/news_item/edit/(.*)', EditNewsItem),
        (r'/news_item/(.*)', ViewNewsItem),
        (r'.*', NotFoundErrorHandler)
        ], debug=True)
    util.run_wsgi_app(app)

if __name__ == '__main__':
    main()
