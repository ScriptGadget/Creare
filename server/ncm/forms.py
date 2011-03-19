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


class MakerForm(djangoforms.ModelForm):
    """ Auto generate a form for adding and editing a Maker store  """
    def clean_store_name(self):
        data=self.clean_data['store_name']
        maker = Maker.all().filter('store_name = ', data).get()
        if maker:
            if not self.instance or self.instance.key() != maker.key():
                raise forms.ValidationError(u'that store name is already taken')
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
            ]

PersonForm = autostrip(MakerForm)

class ProductForm(djangoforms.ModelForm):
    """ Auto generate a form for adding and editing a product  """
    class Meta:
        model = Product
        exclude = ['maker', 'thumb', 'slug', 'disable', 'when']

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
