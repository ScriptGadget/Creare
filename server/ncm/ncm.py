# !/usr/bin/env python
import os
import logging

from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp import util
from google.appengine.api import users
from google.appengine.ext import db
from model import Maker, Product
from gaesessions import get_current_session

class AuthenticatedPage(webapp.RequestHandler):
    def getMakerForUser(self, user):
        """ get the Maker if any associated with this user """
        user_id = user.user_id()
        maker = None

        try:
            makers = Maker.gql("WHERE user_id = :1", user.user_id())
            maker = makers.get()
        except db.KindError:
            maker = None
            logging.debugging.error("Unexpected db.KindError: " + db.KindError);
        return maker;

    def authenticate(self):
        """ Ask a visitor to login before proceeding.  """
        user = users.get_current_user()
        user_id = None
        maker = None

        if not user:
            self.redirect(users.create_login_url(self.request.uri))
        else:
            maker = self.getMakerForUser(user)

        return (user_id, maker)

class Login(AuthenticatedPage):
    """ Just authenticates then redirects to the home page """
    def get(self):
        (user_id, maker) = self.authenticate()
        logging.info('user_id: ' + str(user_id) + ' maker: ' + str(maker));
        if maker:
            session = get_current_session()
            session.start(ssl_only=True)
            session.regenerate_id()
            self.redirect("/maker_store")
        else:
            self.redirect("/register_maker")

class Logout(AuthenticatedPage):
    """ Just kills the session and clears authentication tokens  """
    def get(self):
        session = get_current_session()
        session.terminate()
        self.redirect(users.create_login_url('/'))

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

class MakerRegistrationPage(AuthenticatedPage):
    """ Renders the new maker registration template."""    
    def get(self):
        (user_id, maker) = self.authenticate()

        session = get_current_session()
        session.start(ssl_only=True)
        alerts = session.get('alerts', '')
        template_values = { 'title':'Open Your Store', 'alerts': alerts, 'maker':maker}
        session['alerts'] = ''
        path = os.path.join(os.path.dirname(__file__), "templates/register_maker.html")
        logging.info("Showing Registration Page")
        self.response.out.write(template.render(path, template_values))

    def post(self):
        """ Add a new Maker to the community."""
        try:
            (user_id, maker) = self.authenticate()
            if maker is None and user_id is not None:
                maker = Maker()
                maker.user_id = user_id
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
            maker.phone_number = self.request.get('phone_number')
            maker.mailing_address = self.request.get('mailing_address')
            maker.put()
            logging.debug("Adding or updating  maker == " + maker.full_name)
            self.redirect('/maker_store/'+str(maker.key()))
        except :
            session = get_current_session()
            session['alerts'] = 'An error occured. Please try again'
            self.redirect(self.request.uri)

class HomePage(AuthenticatedPage):
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
        ('/home', HomePage),
        ('/privacy', PrivacyPage),
        ('/terms', TermsPage),
        ('/login', Login),
        ('/logout', Logout),
        (r'/maker_store/(.*)', MakerStorePage),
        (r'/maker_dashboard/(.*)', MakerDashboard),
        (r'/product/(.*)', ProductPage),
        ('/register_maker', MakerRegistrationPage),
        ], debug=True)
    util.run_wsgi_app(app)

if __name__ == '__main__':
    main()
