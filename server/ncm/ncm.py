# !/usr/bin/env python
import os

from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp import util
from google.appengine.api import users
from google.appengine.ext import db
from model import Maker, Product
from gaesessions import get_current_session

class AuthenticatedPage(webapp.RequestHandler):
    def authenticate(self):
        """ Ask a visitor to login before proceeding.  """
        user = users.get_current_user()
        
        user_id = None
        maker = None
        if not user:
            self.redirect(users.create_login_url(self.request.uri))
        else:
            user_id = user.user_id()   
            try:
                makers = Maker.gql("WHERE user_id = :1", user.user_id())
                maker = makers.fetch(1)
            except db.KindError:
                maker = None
        
        return (user_id, maker)

class MakerDashboard(AuthenticatedPage):
    """ Renders a page for Makers to view and manage their catalog and sales """
    def get(self, maker_id):

        (user_id, maker) = self.authenticate()

        if not maker or not maker.key() == maker_id:
            self.redirect("/maker_store/" + maker_id)

        session = get_current_session()
        # if session.is_active():
        c = session.get('counter', 0)
        session['counter'] = c + 1

        template_values = { 'title':'Maker Dashboard', 'maker':maker}
        path = os.path.join(os.path.dirname(__file__), "templates/maker_dashboard.html")
        self.response.out.write(template.render(path, template_values))

class ShopperRegistrationPage(webapp.RequestHandler):
    """ Renders the new user registration template."""    
    def get(self):
        template_values = { 'title':'Register'}
        path = os.path.join(os.path.dirname(__file__), "templates/register_shopper.html")
        self.response.out.write(template.render(path, template_values))

class MakerRegistrationPage(webapp.RequestHandler):
    """ Renders the new maker registration template."""    
    def get(self):
        template_values = { 'title':'Open Your Store'}
        path = os.path.join(os.path.dirname(__file__), "templates/register_maker.html")
        self.response.out.write(template.render(path, template_values))

    def post(self):
        try:
            maker = Maker();
            maker.store_name = self.request.get('store_name')
            maker.store_description = self.request.get('store_description')
            maker.location = self.request.get('location')
            maker.full_name = self.request.get('full_name')
            maker.email = self.request.get('email')
            value = self.request.get('paypal')
            if value.count('@') == 1:
                maker.paypal = value
            else:
                maker.paypal = maker.email
                
                maker.phone = self.request.get('phone')
                maker.mailing_address = self.request.get('mailing_address')
                maker.put()
                self.redirect('/maker_store/'+str(maker.key()))
        except :
            self.redirect(self.request.uri)

class HomePage(webapp.RequestHandler):
    """ Renders the home page template. """
    def get(self):
        q = Product.all()
        results = q.fetch(3)
        stuff = []
        for p in results:
            stuff.append(p)
        template_values = { 'title':'Nevada County Makes', 'stuff':stuff}
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

class ProductPage(webapp.RequestHandler):
    """ Renders a page for a single product. """
    def get(self, product_id):
        product = Product.get(product_id)
        template_values = {'product':product}
        path = os.path.join(os.path.dirname(__file__), "templates/product.html")
        self.response.out.write(template.render(path, template_values))        

def main():
    app = webapp.WSGIApplication([
        ('/', HomePage),
        ('/privacy', PrivacyPage),
        ('/terms', TermsPage),
        (r'/maker_store/(.*)', MakerStorePage),
        (r'/maker_dashboard/(.*)', MakerDashboard),
        (r'/product/(.*)', ProductPage),
        ('/register_maker', MakerRegistrationPage),
        ], debug=True)
    util.run_wsgi_app(app)

if __name__ == '__main__':
    main()
