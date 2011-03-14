import re
from unicodedata import normalize
from google.appengine.ext import db
from gaesessions import get_current_session
import logging
import shardedcounter

_punct_re = re.compile(r'[\t !"#$%&\'()*\-/<=>?@\[\\\]^_`{|},.]+')

def slugify(text, delim=u'-'):
    result = []
    for word in _punct_re.split(text.lower()):
        if word:
            result.append(word)
    return unicode(delim.join(result))

class Community(db.Model):
    """ A Community of Makers and Crafters  """
    name = db.StringProperty(required=True)
    slug = db.StringProperty()
    support_email=db.EmailProperty()
    support_phone=db.PhoneNumberProperty()
    forum_link = db.LinkProperty()

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
    store_name = db.StringProperty(required=True)
    slug = db.StringProperty()
    store_description = db.StringProperty(required=True)
    full_name = db.StringProperty(required=True)
    email = db.EmailProperty(required=True)
    paypal_business_account_email = db.EmailProperty()
    phone_number = db.PhoneNumberProperty(required=True)
    location = db.StringProperty(required=True)
    mailing_address = db.PostalAddressProperty(required=True)
    tags = db.CategoryProperty(required=True)

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

class Product(db.Model):
    """ Something a Maker can sell to a Shopper """
    maker = db.ReferenceProperty(Maker, collection_name='products')
    name = db.StringProperty(required=True)
    slug = db.StringProperty()
    short_description = db.StringProperty(required=True)
    description = db.TextProperty(required=True)
    price = db.FloatProperty(required=True)
    tags = db.CategoryProperty(required=True)
    inventory = db.IntegerProperty(required=True)
    show = db.BooleanProperty(default=True)
    disable = db.BooleanProperty(default=False)

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


class ProductImage(db.Model):
    """ An Image of a Product """
    product = db.ReferenceProperty(Product, collection_name='product_images')
    image = db.BlobProperty()

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

class AdvertisementImage(db.Model):
    """ An Image associated with an Advertisement """
    advertisement = db.ReferenceProperty(Advertisement, collection_name='advertisement_images')
    image = db.BlobProperty()
