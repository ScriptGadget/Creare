# !/usr/bin/env python
import os
import logging

from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp import util
from google.appengine.api import users
from google.appengine.ext import db
from google.appengine.ext.db import djangoforms
from gaesessions import get_current_session

from model import Maker, Product

class MakerForm(djangoforms.ModelForm):
    class Meta:
        model = Maker
        exclude = ['user']

class ProductForm(djangoforms.ModelForm):
    class Meta:
        model = Product
        exclude = ['maker']

class MakerPage(webapp.RequestHandler):
    def get(self):
        authenticator = Authenticator(self)
        (user, maker) = authenticator.authenticate()
        data = MakerForm()
        template_values = { 'title':'Open Your Store', 'maker':maker, 'form' : data}
        path = os.path.join(os.path.dirname(__file__), "templates/register_maker.html")
        logging.info("Showing Registration Page")
        self.response.out.write(template.render(path, template_values))

    def post(self):
        data = MakerForm(data=self.request.POST)
        if data.is_valid():
            # Save the data, and redirect to the view page
            entity = data.save(commit=False)
            entity.put()
            self.redirect('/maker')
        else:
            # Reprint the form
            template_values = { 'title':'Open Your Store', 'maker':maker, 'form' : data}
            path = os.path.join(os.path.dirname(__file__), "templates/register_maker.html")
            logging.info("Showing Registration Page")
            self.response.out.write(template.render(path, template_values))
          
class ProductPage(webapp.RequestHandler):
    def get(self):
        self.response.out.write('<html><body>'
                                '<form method="POST" '
                                'action="/product">'
                                '<table>')
        self.response.out.write(ProductForm())
        self.response.out.write('</table>'
                                '<input type="submit">'
                                '</form></body></html>')

    def post(self):
        data = ProductForm(data=self.request.POST)
        if data.is_valid():
            logging.info('Valid product entry');
            # Save the data, and redirect to the view page
            entity = data.save(commit=False)
            # entity.user = users.get_current_user()
            entity.put()
            self.redirect('/products')
        else:
            # Reprint the form
            self.response.out.write('<html><body>'
                                    '<form method="POST" '
                                    'action="/product">'
                                    '<table>')
            self.response.out.write(data)
            self.response.out.write('</table>'
                                    '<input type="submit">'
                                    '</form></body></html>')

class ProductsPage(webapp.RequestHandler):
    def get(self):
        self.response.out.write('<h2>Products</h2>');
        query = db.GqlQuery("SELECT * FROM Product ORDER BY description")
        for product in query:
            self.response.out.write('<a href="/edit?id=%d">Edit</a> - ' %
                                    product.key().id())
            self.response.out.write("%s - $%0.2f<br>" %
                                    (product.description, product.price))

class EditProductPage(webapp.RequestHandler):
    def get(self):
        id = int(self.request.get('id'))
        product = Product.get(db.Key.from_path('Product', id))
        self.response.out.write('<html><body>'
                                '<form method="POST" '
                                'action="/edit">'
                                '<table>')
        self.response.out.write(ProductForm(instance=product))
        self.response.out.write('</table>'
                                '<input type="hidden" name="_id" value="%s">'
                                '<input type="submit">'
                                '</form></body></html>' % id)
    def post(self):
      id = int(self.request.get('_id'))
      product = Product.get(db.Key.from_path('Product', id))
      data = ProductForm(data=self.request.POST, instance=product)
      if data.is_valid():
          # Save the data, and redirect to the view page
          entity = data.save(commit=False)
          #entity.added_by = users.get_current_user()
          entity.put()
          self.redirect('/products')
      else:
          # Reprint the form
          self.response.out.write('<html><body>'
                                  '<form method="POST" '
                                  'action="/edit">'
                                  '<table>')
          self.response.out.write(data)
          self.response.out.write('</table>'
                                  '<input type="hidden" name="_id" value="%s">'
                                  '<input type="submit">'
                                  '</form></body></html>' % id)

class Authenticator:
    def __init__(self, page):
        self.page = page

    def getMakerForUser(self, user):
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

class Login(webapp.RequestHandler):
    """ Just authenticates then redirects to the home page """
    def get(self):
        authenticator = Authenticator(self)
        (user, maker) = authenticator.authenticate()
        logging.info('Logging in with user: ' + str(user) + ' maker: ' + str(maker));
        if maker:
            session = get_current_session()
            session.start(ssl_only=True)
            session.regenerate_id()
            self.redirect("/maker_store")
        else:
            self.redirect("/maker")

class Logout(webapp.RequestHandler):
    """ Just kills the session and clears authentication tokens  """
    def get(self):
        session = get_current_session()
        session.terminate()
        self.redirect(users.create_login_url('/'))

class MakerDashboard(webapp.RequestHandler):
    """ Renders a page for Makers to view and manage their catalog and sales """
    def get(self, maker_id):

        (user, maker) = self.authenticate()

        if not maker or not maker.key() == maker_id:
            self.redirect("/maker_store/" + maker_id)

        session = get_current_session()
        # if session.is_active():
        c = session.get('counter', 0)
        session['counter'] = c + 1

        template_values = { 'title':'Maker Dashboard', 'maker':maker}
        path = os.path.join(os.path.dirname(__file__), "templates/maker_dashboard.html")
        self.response.out.write(template.render(path, template_values))

class HomePage(webapp.RequestHandler):
    """ Renders the home page template. """
    def get(self):
        user = users.get_current_user()
        maker = None
        if user is not None:
            maker = self.getMakerForUser(user)
        q = Product.all()
        results = q.fetch(3)
        stuff = []
        for p in results:
            stuff.append(p)
        template_values = { 'title':'Nevada County Makes', 'stuff':stuff, 'maker':maker }
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

class MakerStorePage(webapp.RequestHandler):
    """ Renders a store page for a particular maker. """
    def get(self, maker_id):
        maker = Maker.get(maker_id)
        template_values = { 'maker':maker}
        path = os.path.join(os.path.dirname(__file__), "templates/maker_store.html")
        self.response.out.write(template.render(path, template_values))

def main():
    app = webapp.WSGIApplication([
        ('/', HomePage),
        ('/maker', MakerPage),
        ('/product', ProductPage),
        ('/products', ProductsPage),
        ('/edit', EditProductPage),
        ('/home', HomePage),
        ('/privacy', PrivacyPage),
        ('/terms', TermsPage),
        ('/login', Login),
        ('/logout', Logout),
        (r'/maker_store/(.*)', MakerStorePage),
        (r'/maker_dashboard/(.*)', MakerDashboard),
        ], debug=True)
    util.run_wsgi_app(app)

if __name__ == '__main__':
    main()
