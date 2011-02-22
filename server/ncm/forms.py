from google.appengine.ext import db
from google.appengine.ext.db import djangoforms

from model import *

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
    """ Auto generate a form for adding a Community  """
    class Meta:
        model = Community
        exclude = ['slug']

class NewsItemForm(djangoforms.ModelForm):
    """ Auto generate a form for adding a NewsItem  """
    class Meta:
        model = NewsItem
        exclude = ['published', 'community', 'slug']
