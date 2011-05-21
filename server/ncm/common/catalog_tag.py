from google.appengine.ext import webapp
from model import *
import os

register = webapp.template.create_template_register()

def catalog(products, width, maker):
    return {
        'products':products, 
        'width':width,
        'maker':maker,
        }

path = os.path.join(os.path.dirname(__file__), 'catalog_list.html')
register.inclusion_tag(path)(catalog)
