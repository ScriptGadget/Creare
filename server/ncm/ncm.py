# !/usr/bin/env python
import os
import logging
from google.appengine.api import images

from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp import util
from google.appengine.api import users
from google.appengine.ext import db
from google.appengine.ext.db import djangoforms

from gaesessions import get_current_session

from model import Community, Maker, Product, ProductImage, ShoppingCartItem, CartTransaction, MakerTransaction

class MakerForm(djangoforms.ModelForm):
    """ Auto generate a form for adding and editing a Maker store  """
    class Meta:
        model = Maker
        exclude = ['user', 'community']

class ProductForm(djangoforms.ModelForm):
    """ Auto generate a form for adding and editing a product  """
    class Meta:
        model = Product
        exclude = ['maker', 'thumb']

class CommunityForm(djangoforms.ModelForm):
    """ Auto generate a for for adding a Community  """
    class Meta:
        model = Community

class Authenticator:
    def __init__(self, page):
        self.page = page
    @staticmethod
    def getMakerForUser(user):
        """ get the Maker if any associated with this user """
        maker = None

        try:
            makers = Maker.gql("WHERE user = :1", user)
            maker = makers.get()
        except db.KindError:
            maker = None
            logging.debugging.error("Unexpected db.KindError: " + db.KindError);
        return maker;

    def authenticate(self):
        """ Ask a visitor to login before proceeding.  """
        user = users.get_current_user()
        maker = None

        if not user:
            self.page.redirect(users.create_login_url(self.page.request.uri))
        else:
            maker = self.getMakerForUser(user)
        return (user, maker)

    @staticmethod
    def authorized_for(user):
        return user and user == users.get_current_user()

class MakerPage(webapp.RequestHandler):
    """ A page for adding a Maker  """
    def get(self, community_id):
        authenticator = Authenticator(self)
        (user, maker) = authenticator.authenticate()
        if user and maker:
            self.redirect('/maker_dashboard/' + str(maker.key()))
            return
        else:
            data = MakerForm()
            template_values = { 'title':'Open Your Store',
                                'new':True,
                                'form':data,
                                'community':community_id,
                                'uri':self.request.uri}
            path = os.path.join(os.path.dirname(__file__), "templates/maker.html")
            logging.info("Showing Registration Page")
            self.response.out.write(template.render(path, template_values))

    def post(self, community_id):
        data = MakerForm(data=self.request.POST)
        if data.is_valid():
            # Save the data, and redirect to the view page
            entity = data.save(commit=False)
            entity.user = users.get_current_user()
            entity.community = Community.get(community_id)
            entity.put()
            logging.info('User: ' + str(entity.user) + ' has joined ' + entity.community.name)
            self.redirect('/community/' + str(entity.community.key()))
        else:
            # Reprint the form
            template_values = { 'title':'Open Your Store', 
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
              self.redirect('/')
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
        (user, maker) = authenticator.authenticate()
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
        (user, maker) = authenticator.authenticate()
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
        (user, maker) = authenticator.authenticate()
        if not maker:
            self.redirect('/')
            return
        else:
            product = Product.get(id)
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
      (user, maker) = authenticator.authenticate()
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
              for product_image in entity.product_images:
                  product_image.delete()
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
              template_values = { 'form' : ProductForm(instance=product), 
                                  'maker' : maker,
                                  'id' : id, 'uri':self.request.uri}
              path = os.path.join(os.path.dirname(__file__), "templates/product.html")
              self.response.out.write(template.render(path, template_values))

class Login(webapp.RequestHandler):
    """ Just authenticates then redirects to the home page """
    def get(self, community_id):
        authenticator = Authenticator(self)
        (user, maker) = authenticator.authenticate()

        if maker:
            session = get_current_session()
            # session.start(ssl_only=True)
            session.regenerate_id()
            self.redirect('/community/%s/maker/maker_dashboard/%s' % (community_id, str(maker.key())))
        else:
            self.redirect('/community/%s/maker/add' % community_id)

class Logout(webapp.RequestHandler):
    """ Just kills the session and clears authentication tokens  """
    def get(self, community_id):
        session = get_current_session()
        session.terminate()
        self.redirect(users.create_logout_url('/community/'+ community_id))

class CommunityHomePage(webapp.RequestHandler):
    """ Renders the home page template. """
    def get(self, community_id):
        try:
            community = db.get(community_id)
        except:
            self.error(404)
            self.response.out.write("I don't recognize that community")
            return

        user = users.get_current_user()
        maker = None
        if user is not None:
            maker = Authenticator.getMakerForUser(user)

        stuff = Product.all()
        products = []
        for product in stuff:
            if str(product.maker.community.key()) == community_id:
                products.append(product)

        template_values = { 'title': community.name + ' Makes', 
                            'community':community,
                            'products':products, 'maker':maker}

        session = get_current_session()        
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
        (user, maker) = authenticator.authenticate()

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
        logging.info('RemoveProductFromCart: ' + str(product_id))
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
        
        message = '{"products":['
        for item in items:
            product = Product.get(item.product)
            message += "{\"count\":\"%s\",\"key\":\"%s\",\"name\":\"%s\"}," % (item.count, product.key(), product.name)
        message += ']}'
        logging.info(message)
        self.response.out.write(message)

class AddCommunityPage(webapp.RequestHandler):
    """ A page for adding a Community  """
    def get(self):
        authenticator = Authenticator(self)
        (user, maker) = authenticator.authenticate()
        if user and users.is_current_user_admin():
            data = CommunityForm()
            template_values = { 'title':'Create a Community',
                                'form':data, 
                                'uri':self.request.uri}
            path = os.path.join(os.path.dirname(__file__), "templates/community.html")
            self.response.out.write(template.render(path, template_values))

    def post(self):
        data = CommunityForm(data=self.request.POST)
        if data.is_valid():
            # Save the data, and redirect to the view page
            entity = data.save(commit=False)
            entity.put()
            self.redirect('/')
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
        message = '<h2>Please visit one of our communities instead</h2>'
        for community in communities:
            message += '<p><a href="%s">%s</a></p>' % ('/community/'+str(community.key()),community.name)
        self.response.out.write(message)

class CheckoutPage(webapp.RequestHandler):
    def get(self, community_id):
        try:
            community = Community.get(community_id)
        except:
            self.error(404)
            self.response.out.message("I don't recognize that community.")
            return

        session = get_current_session()
        if not session.is_active():
            self.response.out.write("I don't see anything in your cart")
            return
        else:
            items = session.get('ShoppingCartItems', [])
            products = []
            for item in items:
                product = Product.get(item.product)
                product.count = item.count
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
    def get(self):
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
            for item in items:
                product = Product.get(item.product)
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

            self.response.out.write("{ \"message\":\"" 
                                    + "Thank you for your order."
                                    + "\"}")
            session.pop('ShoppingCartItems')
            return

def main():
    app = webapp.WSGIApplication([
        ('/', SiteHomePage),
        ('/maker', MakerPage),
        (r'/community/(.*)/maker/add', MakerPage),
        (r'/maker/edit/(.*)', EditMakerPage),
        ('/maker/edit', EditMakerPage),
        ('/product/add', ProductPage),
        (r'/product/edit/(.*)', EditProductPage),
        ('/product/edit', EditProductPage),
        ('/privacy', PrivacyPage),
        ('/terms', TermsPage),
        (r'/community/(.*)/login', Login),
        (r'/logout/(.*)', Logout),
        (r'/maker_store/(.*)', MakerStorePage),
        (r'/maker_dashboard/(.*)', MakerDashboard),
        (r'/product_images/(.*)', DisplayImage),
        ('/upload_product_image', UploadProductImage), 
        ('/AddProductToCart', AddProductToCart),
        ('/RemoveProductFromCart', RemoveProductFromCart),
        ('/community/add', AddCommunityPage),
        (r'/community/(.*)', CommunityHomePage),
        (r'/checkout/(.*)', CheckoutPage),
        ('/OrderProductsInCart', OrderProductsInCart),
        (r'.*', NotFoundErrorHandler)
        ], debug=True)
    util.run_wsgi_app(app)

if __name__ == '__main__':
    main()
