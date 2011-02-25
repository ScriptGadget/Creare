import re
from unicodedata import normalize
from google.appengine.ext import db

_punct_re = re.compile(r'[\t !"#$%&\'()*\-/<=>?@\[\\\]^_`{|},.]+')

def slugify(text, delim=u'-'):
    """Generates an slightly worse ASCII-only slug."""
    result = []
    for word in _punct_re.split(text.lower()):
        word = normalize('NFKD', word).encode('ascii', 'ignore')
        if word:
            result.append(word)
    return unicode(delim.join(result))

class Community(db.Model):
    """ A Community of Makers and Crafters  """
    name = db.StringProperty(required=True)
    slug = db.StringProperty()
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
    def get_current_community(community_slug, session):
        if community_slug:
            community = Community.get_community_for_slug(community_slug)
        else:
            community = Community.get_community_for_slug(session.get('community',''))

        return community
        

class CommunityManager(db.Model):
    """ A Person Who can Approve Makers and Manage a Community Site """
    community = db.ReferenceProperty(Community, collection_name='community_managers')
    user = db.UserProperty(required=True)
    name = db.StringProperty(required=True)    

class Maker(db.Model):
    """ Someone who sells products  """
    user = db.UserProperty()
    community = db.ReferenceProperty(Community, collection_name='makers')
    store_name = db.StringProperty(required=True)
    slug = db.StringProperty()
    store_description = db.StringProperty(required=True)
    full_name = db.StringProperty(required=True)
    email = db.EmailProperty(required=True)
    paypal = db.EmailProperty()
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

class ProductImage(db.Model):
    """ An Image of a Product """
    product = db.ReferenceProperty(Product, collection_name='product_images')
    image = db.BlobProperty()

class ShoppingCartItem():
    """ This is not a Model and does not persist! """
    def __init__(self, product = '', count = 0):
        self.product = product
        self.count = count

class CartTransaction(db.Model):
    """ Represents an entire shopping cart, potentially with multiple
    Products by multiple Makers. The data is only valid for a moment in
    time, so it keeps a copy of prices and counts as they were at the moment
    of purchase."""
    timestamp = db.DateTimeProperty(auto_now_add=True)
    transaction_type = db.CategoryProperty(['Sale', 'Payout', 'Refund'])
    note = db.TextProperty()
    authorization = db.StringProperty()

class MakerTransaction(db.Model):
    """ Represents a single Maker's portion of a transaction. """
    maker = db.ReferenceProperty(Maker, 
                                 collection_name="maker_transaction", 
                                 required=True)    
    detail = db.StringListProperty()


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
    community = db.ReferenceProperty(Community, collection_name='community_advertisements')
    name = db.StringProperty()
    slug = db.StringProperty()
    contact_name = db.StringProperty()
    contact_email = db.EmailProperty()
    hover_text = db.StringProperty()
    url = db.LinkProperty()
    # rotation = db.CategoryProperty(['High', 'Medium', 'Low'])
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

class AdvertisementImage(db.Model):
    """ An Image associated with an Advertisement """
    advertisement = db.ReferenceProperty(Advertisement, collection_name='advertisement_images')
    image = db.BlobProperty()
