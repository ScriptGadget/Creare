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
from unicodedata import normalize
from google.appengine.ext import db
from gaesessions import get_current_session
import logging
import shardedcounter
import hashlib
import datetime as datetime_module

_default_categories = ['Unclassifiable', 'Bags & Totes', 'Jewelry', 'Clothing', 'Food', 'Napkins & Linens & The Like', 'Soap & Skin Care', 'Pictures (Fine Art & Photographs)', 'Sculptures & Pottery', 'Toys & Games', 'Gears & Gadgets', 'Wellness & Therapeutic', 'Metalwork', 'Woodwork', 'Cards & Papercraft']

_punct_re = re.compile(r'[\t !"#$%&\()*\-/<=>?@\[\\\]^_`{|},.]+')
_word_re = re.compile('[\W]+')

def slugify(text, delim=u'-'):
    result = []
    for word in _punct_re.split(text.lower()):
        if word:
            result.append(_word_re.sub('', word))

    return unicode(delim.join(result))

class Utc_tzinfo(datetime_module.tzinfo):
    def utcoffset(self, dt): return datetime_module.timedelta(0)
    def dst(self, dt): return datetime_module.timedelta(0)
    def tzname(self, dt): return 'UTC'
    def olsen_name(self): return 'UTC'

class Pacific_tzinfo(datetime_module.tzinfo):
    """Implementation of the Pacific timezone. From GAE docs."""
    def utcoffset(self, dt):
        return datetime_module.timedelta(hours=-8) + self.dst(dt)

    def _FirstSunday(self, dt):
        """First Sunday on or after dt."""
        return dt + datetime_module.timedelta(days=(6-dt.weekday()))

    def dst(self, dt):
        # 2 am on the second Sunday in March
        dst_start = self._FirstSunday(datetime_module.datetime(dt.year, 3, 8, 2))
        # 1 am on the first Sunday in November
        dst_end = self._FirstSunday(datetime_module.datetime(dt.year, 11, 1, 1))

        if dst_start <= dt.replace(tzinfo=None) < dst_end:
            return datetime_module.timedelta(hours=1)
        else:
            return datetime_module.timedelta(hours=0)
    def tzname(self, dt):
        if self.dst(dt) == datetime_module.timedelta(hours=0):
            return "PST"
        else:
            return "PDT"

#common validators
def validateEmail(value):
    if len(value) > 255:
        raise db.BadValueError("Email address too long")
    allowed = re.compile("[a-z0-9.\-_]+@[0-9a-z\-]+\.[0-9a-z\-]+", re.IGNORECASE)
    if not allowed.match(value):
        raise db.BadValueError("Bad email address: " + value)


class Community(db.Model):
    """ A Community of Makers and Crafters  """
    name = db.StringProperty(required=True)
    slug = db.StringProperty()
    support_email=db.EmailProperty()
    support_phone=db.PhoneNumberProperty()
    forum_link = db.LinkProperty()
    coordinator_names = db.StringProperty()
    description = db.TextProperty()
    address = db.PostalAddressProperty()

    fee_percentage = db.FloatProperty(required=True, default=10.0)
    fee_minimum = db.FloatProperty(required=True, default=0.30)
    paypal_fee_percentage = db.FloatProperty(required=True, default=2.9)
    paypal_fee_minimum = db.FloatProperty(required=True, default=0.30)
    use_sandbox = db.BooleanProperty(default=True)

    # Sandbox stuff
    paypal_sandbox_business_id = db.StringProperty()
    paypal_sandbox_email_address = db.StringProperty()
    paypal_sandbox_api_username = db.StringProperty()
    paypal_sandbox_api_password = db.StringProperty()
    paypal_sandbox_api_signature = db.StringProperty()
    paypal_sandbox_application_id = db.StringProperty()

    # Live Stuff
    paypal_business_id = db.StringProperty()
    paypal_email_address = db.StringProperty()
    paypal_api_username = db.StringProperty()
    paypal_api_password = db.StringProperty()
    paypal_api_signature = db.StringProperty()
    paypal_application_id = db.StringProperty()

    # Site Stuff
    featured_maker = db.StringProperty()
    motto = db.StringProperty()
    twitter_account = db.StringProperty()

    @property
    def business_id(self):
        if self.use_sandbox:
            return self.paypal_sandbox_business_id
        else:
            return self.paypal_business_id

    @property
    def email_address(self):
        if self.use_sandbox:
            return self.paypal_sandbox_email_address
        else:
            return self.paypal_email_address

    @property
    def api_username(self):
        if self.use_sandbox:
            return self.paypal_sandbox_api_username
        else:
            return self.paypal_api_username

    @property
    def api_password(self):
        if self.use_sandbox:
            return self.paypal_sandbox_api_password
        else:
            return self.paypal_api_password
    
    @property
    def api_signature(self):
        if self.use_sandbox:
            return self.paypal_sandbox_api_signature
        else:
            return self.paypal_api_signature

    @property
    def application_id(self):
        if self.use_sandbox:
            return self.paypal_sandbox_application_id
        else:
            return self.paypal_application_id

    @property
    def photo(self):
        return Image.all(keys_only=True).filter('category =', 'Portrait').ancestor(self).get()

    @property
    def logo(self):
        return Image.all(keys_only=True).filter('category =', 'Logo').ancestor(self).get()

    @property
    def timeZone(self):
        """ 
        For now just return Pacific TZ. 
        The more general case is going to take alot of work.
        """
        return Pacific_tzinfo()

    @property
    def categories(self):
        return _default_categories

    @staticmethod
    def get_community_for_slug(slug):
        try:
            q = Community.gql('WHERE slug = :1', slug)
            community = q.get()
            if community:
                return community
        except:
            pass

        return None

    @staticmethod
    def get_slug_for_name(name):
        return slugify(name)

    @staticmethod
    def get_current_community(community_slug=None, session=None):
        community = None

        if community_slug:
            community = Community.get_community_for_slug(community_slug)
        else:
            if not session:
                session = get_current_session();
            community = Community.get_community_for_slug(session.get('community',''))
            if not community:
                q = db.Query(Community, True)
                if q:
                    key = q.get()
                    if key:
                        community = Community.get(key)

        return community

    @property
    def maker_score(self):
        return shardedcounter.get_count('maker_score')

    @property
    def product_score(self):
        return shardedcounter.get_count('product_score')

    @property
    def pending_score(self):
        return shardedcounter.get_count('pending_score')
    
    def increment_maker_score(self):
        shardedcounter.increment('maker_score', 1)

    def increment_product_score(self):
        shardedcounter.increment('product_score', 1)

    def increment_pending_score(self):
        shardedcounter.increment('pending_score', 1)

    def decrement_pending_score(self):
        shardedcounter.decrement('pending_score')

class Page(db.Model):
    """ A miscellaneous content page like About, Privacy Policy, etc.  """
    name = db.StringProperty(required=True)
    content = db.TextProperty(required=True, default='Add Content Here.')

class CommunityManager(db.Model):
    """ A Person Who can Approve Makers and Manage a Community Site """
    community = db.ReferenceProperty(Community, collection_name='community_managers')
    user = db.UserProperty(required=True)
    name = db.StringProperty(required=True)

class Maker(db.Model):
    """ Someone who sells products  """
    user = db.UserProperty()
    joined = db.DateTimeProperty(auto_now_add=True)
    approval_status = db.StringProperty(choices=set(['Review','Approved','Rejected_Location', 'Rejected_Other']), default='Review')
    community = db.ReferenceProperty(Community, collection_name='makers')
    store_name = db.StringProperty(required=True, verbose_name="Your store name")
    slug = db.StringProperty()
    full_name = db.StringProperty(required=True, verbose_name="Your name")
    email = db.EmailProperty(required=True, verbose_name="Your email")
    website = db.LinkProperty()
    paypal_business_account_email = db.EmailProperty(verbose_name="Paypal business or premier account email", validator=validateEmail)
    phone_number = db.PhoneNumberProperty(required=True)
    mailing_address = db.PostalAddressProperty(required=True)
    store_description = db.TextProperty(required=True, verbose_name="About you and your creations")
    location = db.TextProperty(required=True, verbose_name="Store Location, Market Booth, Maker Space")
    tags = db.StringListProperty(required=True, verbose_name="Comma Separated Keywords")
    accepted_terms = db.BooleanProperty(required=False)

    @property
    def photo(self):
        return Image.all(keys_only=True).filter('category =', 'Portrait').ancestor(self).get()

    @property
    def logo(self):
        return Image.all(keys_only=True).filter('category =', 'Logo').ancestor(self).get()

    @property
    def tag_string(self):
        return ','.join(self.tags)

    @staticmethod
    def get_maker_for_slug(slug):
        try:
            q = Maker.gql('WHERE slug = :1', slug)
            maker = q.get()
            if maker:
                return maker
        except:
            pass

        return None

    @staticmethod
    def get_slug_for_store_name(store_name):
        return slugify(store_name)

    @staticmethod
    def getMakerForUser(user):
        """ get the Maker if any associated with this user """
        maker = None

        if user:
            try:
                makers = Maker.gql("WHERE user = :1", user)
                maker = makers.get()
            except db.KindError:
                maker = None
                logging.debugging.error("Unexpected db.KindError: " + db.KindError)

        return maker;

class Product(db.Model):
    """ Something a Maker can sell to a Shopper """
    maker = db.ReferenceProperty(Maker, collection_name='products')
    name = db.StringProperty(required=True, verbose_name="Item name (be careful, cannot be changed)")
    slug = db.StringProperty()
    short_description = db.StringProperty(required=True, verbose_name="three related, descriptive words")
    description = db.TextProperty(required=True, verbose_name="Everything amazing about your item")
    price = db.FloatProperty(required=True, verbose_name="Price with shipping/handling and tax (no $ or commas)", default=10.0)
    discount_price = db.FloatProperty(required=False, verbose_name="Optional Discounted Price")
    tags = db.StringListProperty(required=True, verbose_name="Tags (search terms separated by commas)")
    unique = db.BooleanProperty(default=False)
    inventory = db.IntegerProperty(required=True, verbose_name="Number of items you have to sell", default=1)
    show = db.BooleanProperty(default=True, verbose_name="Show this item to shoppers")
    disable = db.BooleanProperty(default=False)
    when = db.StringProperty()
    pickup_only = db.BooleanProperty(default=False, verbose_name="Pick-up only")
    category = db.StringProperty(choices=set(_default_categories), default=_default_categories[0], required=True)
    video_link = db.StringProperty(verbose_name="Embedded Video Link")

    @property
    def image(self):
        return Image.all(keys_only=True).ancestor(self).get()

    @property
    def tag_string(self):
        return ','.join(self.tags)

    @property
    def actual_price(self):
        price = self.price
        if self.discount_price > 0.98:
            price = self.discount_price
        return price

    @staticmethod
    def get_product_for_slug(slug):
        try:
            q = Product.gql('WHERE slug = :1', slug)
            product = q.get()
            if product:
                return product
        except:
            pass

        return None

    @staticmethod
    def get_slug_for_name(name):
        return slugify(name)

    @staticmethod
    def decrement_product_inventory(product_key, sold):
        """ 
        Here we can wrap the inventory decrement in a transaction. 
        If we ever really need to scale this we could do it with 
        a sharded counter and keep a high water mark for inventory
        instead of a count, but that's probably uneeded 
        this size site.
        """
        
        product = Product.get(product_key)
        product.inventory -= sold
        if product.inventory < 0:
            product.inventory = 0
        product.put()

    @staticmethod
    def findProductsByTag(tag):
        """ Finds products by a single tag. """
        p = Product.all()
        p.filter('show =', True)
        p.filter('disable = ', False)
        p.filter( 'tags =', tag)
        return p

    @staticmethod
    def searchByTag(tags):
        """ Search for a product by one or more tags  """
        p = []
        for tag in tags.split(" "):
            tag = tag.strip().lower()
            p.extend(Product.findProductsByTag(tag).fetch(1000))
        nodups = {}
        for product in p:
            if not product.key() in nodups and product.maker.approval_status == 'Approved':
                nodups[product.key()] = product
        return nodups.values()

    @staticmethod
    def findProductsByCategory(category, number_to_return=9, where_to_start=0):
        p = Product.all()
        p.filter('show =', True)
        p.filter('disable = ', False)
        if category:
            p.filter('category = ', category)
        p.order('-when')
        return p.fetch(number_to_return, where_to_start)
    
    @staticmethod
    def getLatest(number_to_return):
        """ Get one item from the four stores with the most recent updates """
        stuff = Product.all()
        stuff.order('-when')
        latest = []
        makers = set([])
        count = 0;
        for product in stuff:
            if  product.show and not product.disable and product.maker.approval_status == 'Approved' and product.maker.key() not in makers:
                latest.append(product)
                makers.add(product.maker.key())
                count += 1
                if count >= number_to_return:
                    break;
        return latest;

    @staticmethod
    def getFeatured(number_to_return, community):
        """ Get four products from the featured Maker """
        if community.featured_maker:
            maker = Maker.get(community.featured_maker)
            stuff = maker.products 
            products = []
            count = 0
            for product in stuff:
                if product.show and not product.disable:
                    products.append(product)
                    count += 1
                    if count >= 4:
                        break;
            return (maker, products)
        else:
            return (None, None)

    @staticmethod
    def buildWhenStamp(maker):
        """ Build a when stamp for sorting based on the Maker's key."""
        return "%s|%s" % (datetime_module.datetime.now(), hashlib.md5(str(maker.key())).hexdigest())

class ShoppingCartItem():
    """ This is not a db.Model and does not persist! """
    def __init__(self, product_key, price, count = 0):
        self.product_key = product_key
        self.price = price
        self.count = count

    @property
    def subtotal(self):
        return self.price * self.count

    @staticmethod
    def createReceiverList(community, shopping_cart_items):
        """
        Build a dict of recipients and amounts from a shopping cart. The dict contains
        one entry containing a tuple which in turn contains the payment id and amount
        for the primary recipient and one entry which is a list of tuples of payment ids
        and amounts for all other recipients.
        """
        total_amount = 0.0
        makers = {}
        for item in shopping_cart_items:
            subtotal = item.count * item.price
            total_amount += subtotal
            product = Product.get(item.product_key)
            if product.maker.key() in makers:
                (email, amount) = makers[product.maker.key()]
                makers[product.maker.key()] = (email, amount + subtotal)
            else:
                makers[product.maker.key()] = (product.maker.paypal_business_account_email, subtotal)

        combined_fee_factor = (community.fee_percentage + community.paypal_fee_percentage) * 0.01
        combined_fee_minimum = community.fee_minimum + community.paypal_fee_minimum

        for key in makers:
            (email, amount) = makers[key]
            makers[key] = (email, amount - (amount * combined_fee_factor) - combined_fee_minimum)

        if community.use_sandbox:
            primary_email = community.paypal_sandbox_business_id
        else:
            primary_email = community.paypal_business_id

        return {'primary':(primary_email, total_amount), 'others':makers.values()}

class CartTransaction(db.Model):
    """ Represents an entire shopping cart, potentially with multiple
    Products by multiple Makers. The data is only valid for a moment in
    time, so it keeps a copy of prices and counts as they were at the moment
    of purchase. """
    timestamp = db.DateTimeProperty(auto_now_add=True)
    transaction_type = db.StringProperty(choices=set(['Sale']), default='Sale', required=True)
    transaction_status = db.StringProperty(choices=set(['UNSUBMITTED', 'CREATED', 'ERROR', 'REVERSALERROR', 'COMPLETED', 'INCOMPLETE']), default='UNSUBMITTED', required=True)
    error_details = db.StringProperty()
    paypal_pay_key = db.StringProperty()
    shopper_name = db.StringProperty()
    shopper_email = db.EmailProperty()
    shopper_phone = db.PhoneNumberProperty()
    shopper_shipping = db.PostalAddressProperty()
    note = db.StringProperty()
    transaction_history = db.TextProperty()

class MakerTransaction(db.Model):
    """ Represents a single Maker's portion of a transaction. """
    maker = db.ReferenceProperty(Maker,
                                 collection_name="maker_transaction",
                                 required=True)
    email = db.EmailProperty() #de-normalize for transactions in IPN handling
    detail = db.StringListProperty()
    shipped = db.BooleanProperty(required=True, default=False)
    when = db.StringProperty(required=True)
    status = db.StringProperty(choices=set(['Pending', 'Paid', 'Error']), default='Pending', required=True)
    messages = db.StringProperty()

# NewsItems, EventNotices and TipItems  are similar
# but they are never logically managed together
# so we don't bother with a PolyModel

class NewsItem(db.Model):
    """ Local news relevant to makers  """
    community = db.ReferenceProperty(Community, collection_name='community_news_items')
    title = db.StringProperty()
    slug = db.StringProperty()
    created = db.DateTimeProperty(auto_now_add=True)
    text = db.TextProperty()
    summary = db.StringProperty()
    show = db.BooleanProperty()

    @staticmethod
    def get_news_item_for_slug(slug):
        try:
            q = NewsItem.gql('WHERE slug = :1', slug)
            news_item = q.get()
            if news_item:
                return news_item
        except:
            pass

        return None

    @staticmethod
    def get_slug_for_title(title):
        return slugify(title)

class EventNotice(db.Model):
    """ A community event like a sack lunch or a meet and greet """
    community = db.ReferenceProperty(Community, collection_name='community_event_notice')
    title = db.StringProperty()
    time = db.DateTimeProperty()
    text = db.TextProperty()
    summary = db.StringProperty()
    show = db.BooleanProperty()

class TipItem(db.Model):
    """ A hint or tip about how to use the site or a creative howto  """
    community = db.ReferenceProperty(Community, collection_name='community_tip_item')
    title = db.StringProperty()
    text = db.TextProperty()
    summary = db.StringProperty()
    show = db.BooleanProperty()

class AuthenticationException(Exception):
    pass

class Advertisement(db.Model):
    """ An advertisement. """
    community = db.ReferenceProperty(Community, collection_name='community_advertisements')
    created = db.DateTimeProperty(auto_now_add=True)
    last_shown = db.DateTimeProperty(auto_now=True)
    name = db.StringProperty()
    slug = db.StringProperty()
    contact_name = db.StringProperty()
    contact_email = db.EmailProperty()
    hover_text = db.StringProperty()
    url = db.LinkProperty()
    show = db.BooleanProperty(default=False)
    PSA = db.BooleanProperty(default=False)
    notes = db.StringProperty()

    @property
    def image(self):
        return Image.all(keys_only=True).ancestor(self).get()

    @staticmethod
    def get_slug_for_name(name):
        return slugify(name)

    @staticmethod
    def get_advertisement_for_slug(slug):
        try:
            q = Advertisement.gql('WHERE slug = :1', slug)
            advertisement = q.get()
            if advertisement:
                return advertisement
        except:
            pass

        return None

    def remaining_impressions(self):
        return shardedcounter.get_count(str(self.key()))

    def decrement_impressions(self):
        shardedcounter.decrement(str(self.key()))

    def refill_impressions(self, impressions):
        shardedcounter.increment(str(self.key()), impressions)

class Image(db.Model):
    """ 
    An icon, photo or graphic. 
    Use ancestry to associate with Makers, Products and Communities.
    """
    category = db.StringProperty(choices=set(['Product','Advertisement','Portrait','Logo','Banner']), required=True)
    content = db.BlobProperty(required=True)
