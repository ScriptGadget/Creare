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
import re
from urlparse import urljoin
from BeautifulSoup import BeautifulSoup, Comment
from google.appengine.ext import db

try:
  from django import newforms as forms
except ImportError:
  from django import forms

from google.appengine.ext.db import djangoforms

from model import *

def autostrip(cls):
    """
    From http://djangosnippets.org/snippets/956/
    since http://code.djangoproject.com/ticket/6362 seems to be stuck in committee
    """
    fields = [(key, value) for key, value in cls.base_fields.iteritems() if isinstance(value, forms.CharField)]
    for field_name, field_object in fields:
        def get_clean_func(original_clean):
            return lambda value: original_clean(value and value.strip())
        clean_func = get_clean_func(getattr(field_object, 'clean'))
        setattr(field_object, 'clean', clean_func)
    return cls


def sanitizeHtml(value, base_url=None):
    """ From an example on StackOverflow 
        http://stackoverflow.com/questions/16861/sanitising-user-input-using-python
    """
    rjs = r'[\s]*(&#x.{1,7})?'.join(list('javascript:'))
    rvb = r'[\s]*(&#x.{1,7})?'.join(list('vbscript:'))
    re_scripts = re.compile('(%s)|(%s)' % (rjs, rvb), re.IGNORECASE)
    validTags = 'p i strong b u a h1 h2 h3 pre br img'.split()
    validAttrs = 'href src width height'.split()
    urlAttrs = 'href src'.split() # Attributes which should have a URL
    soup = BeautifulSoup(value)
    for comment in soup.findAll(text=lambda text: isinstance(text, Comment)):
        # Get rid of comments
        comment.extract()
    for tag in soup.findAll(True):
        if tag.name not in validTags:
            tag.hidden = True
        attrs = tag.attrs
        tag.attrs = []
        for attr, val in attrs:
            if attr in validAttrs:
                val = re_scripts.sub('', val) # Remove scripts (vbs & js)
                if attr in urlAttrs:
                    val = urljoin(base_url, val) # Calculate the absolute url
                tag.attrs.append((attr, val))

    return soup.renderContents().decode('utf8')

"""
From http://stackoverflow.com/questions/4960445/django-display-a-comma-separated-list-of-manytomany-items-in-a-charfield-on-a-m
It would have been nice to be able to do something like this, but 
djangoforms.py breaks overriding to_python() and provides decidedly odd
default view for a StringListProperty (newline separated in a text area)
which won't help us at all for comma separated tags.

class CommaTags(forms.Widget):
    def render(self, name, value, attrs=None):      
      final_attrs = self.build_attrs(attrs, type='text', name=name)
      values = []
      if value:
        for each in value.split('\n'):
          values.append(str(each).encode('ascii'))
          value = ','.join(values)
      else:
        value = ''
        return u'<input type="text" value="%s"/>' % value

class CommaField(forms.CharField):
    def to_python(self, value):
      logging.info('to_python:' + str(value))
      tags = []
      for tag in value.split(","):
        tags.append(unicode(tag.strip()).encode('ascii'))
      return tags
"""
class MakerForm(djangoforms.ModelForm):
    """ Auto generate a form for adding and editing a Maker store  """
    # won't work (see above)
    # tags = CommaField(label="Comma separated keywords", widget=CommaTags())
   
    def __init__(self, *args, **kwargs):
        super(MakerForm, self).__init__(*args, **kwargs)
        instance = getattr(self, 'instance', None)
        if instance:
            self.fields['store_name'].widget.attrs['readonly'] = True
        else:
          self.fields['store_name'].widget.attrs.pop('readonly',None)

    def clean_store_name(self):
        data=self.clean_data['store_name']

        if self.instance:
          if self.instance.store_name != data:
            raise forms.ValidationError(u'Store names cannot be changed.')

        maker = Maker.all().filter('store_name = ', data).get()
        if maker:
            if not self.instance or self.instance.key() != maker.key():
                raise forms.ValidationError(u'That store name is already taken.')
        return data

    class Meta:
        model = Maker
        exclude = [
            'user',
            'community',
            'slug',
            'timestamp',
            'approval_status',
            'accepted_terms',
            'tags',
            ]

PersonForm = autostrip(MakerForm)

class ProductForm(djangoforms.ModelForm):
    """ Auto generate a form for adding and editing a product  """
    def __init__(self, data=None, instance=None, maker=None):
      djangoforms.ModelForm.__init__(self, data=data, instance=instance)
      self.maker = maker
      if instance:
        self.fields['name'].widget.attrs['readonly'] = True
      else:
        self.fields['name'].widget.attrs.pop('readonly',None)

    def clean_name(self):
        data=self.clean_data['name']

        if self.instance:
          if self.instance.name != data:
            raise forms.ValidationError(u'Product names cannot be changed')
        else:
          if self.maker:
            p = Product.all()
            p.filter('name = ', data)
            p.filter('maker == ', self.maker.key())
            product = p.get()
            if product:
              raise forms.ValidationError(u'You already have a product by that name.')

        return data

    def clean_price(self):
      """ This would have been better as a validator, but adding a validator seems problematic with the GAE ModelForm."""
      data=self.clean_data['price']
      if float(data) < 0.99:
        raise forms.ValidationError(u"Prices must be greater than $0.98")
      return data

    def clean_discount_price(self):
      """ This would have been better as a validator, but adding a validator seems problematic with the GAE ModelForm."""
      data=self.clean_data['discount_price']
      if not data is None and not len(data) == 0:
        if float(data) < 0.99:
          raise forms.ValidationError(u"Prices must be greater than $0.98")
      return data

    class Meta:
        model = Product
        exclude = [
          'maker',
          'thumb',
          'slug',
          'disable',
          'when',
          'tags',
          ]

ProductForm = autostrip(ProductForm)

class CommunityForm(djangoforms.ModelForm):
    """ Auto generate a form for adding a Community  """
    class Meta:
        model = Community
        exclude = ['slug']

CommunityForm = autostrip(CommunityForm)

class NewsItemForm(djangoforms.ModelForm):
    """ Auto generate a form for adding a NewsItem  """
    class Meta:
        model = NewsItem
        exclude = ['published', 'community', 'slug']

NewsItemForm = autostrip(NewsItemForm)

class AdvertisementForm(djangoforms.ModelForm):
    """ Auto generate a form for adding and editing an advertisment  """
    class Meta:
        model = Advertisement
        exclude = ['slug', 'community', 'rotation', 'created']

AdvertismentForm = autostrip(AdvertisementForm)
