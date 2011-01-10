# !/usr/bin/env python
import os

from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp import util
from google.appengine.api import users
from google.appengine.ext import db
from model import Maker, Product

class HomePage(webapp.RequestHandler):
    """ Renders the home page template."""
    def get(self):
        q = Product.all()
        results = q.fetch(3)
        stuff = []
        for p in results:
            stuff.append(p)
        template_values = { 'title':'Nevada County Makes', 'stuff':stuff}
        path = os.path.join(os.path.dirname(__file__), "templates/home.html")
        self.response.out.write(template.render(path, template_values))

class MakerStorePage(webapp.RequestHandler):
    """ Renders a store page for a particular maker."""
    def get(self, maker_id):
        maker = Maker.get(maker_id)
        template_values = { 'maker':maker}
        path = os.path.join(os.path.dirname(__file__), "templates/maker_store.html")
        self.response.out.write(template.render(path, template_values))

class ProductPage(webapp.RequestHandler):
    """ Renders a page for a single product."""
    def get(self, product_id):
        product = Product.get(product_id)
        template_values = {'product':product}
        path = os.path.join(os.path.dirname(__file__), "templates/product.html")
        self.response.out.write(template.render(path, template_values))        

def main():
    app = webapp.WSGIApplication([
        ('/', HomePage),
        (r'/maker_store/(.*)', MakerStorePage),
        (r'/product/(.*)', ProductPage),
        ], debug=True)
    util.run_wsgi_app(app)

if __name__ == '__main__':
    main()
