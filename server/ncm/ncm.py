# !/usr/bin/env python
import os

from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp import util
from google.appengine.api import users
from google.appengine.ext import db

class HomePage(webapp.RequestHandler):
    """ Renders the home page template."""
    def get(self):
        stuff = ['thing one', 'thing two', 'thing three']
        template_values = { 'title':'Nevada County Makes', 'stuff':stuff}
        path = os.path.join(os.path.dirname(__file__), "templates/home.html")
        self.response.out.write(template.render(path, template_values))

def main():
    app = webapp.WSGIApplication([
        ('/', HomePage),
        ], debug=True)
    util.run_wsgi_app(app)

if __name__ == '__main__':
    main()
