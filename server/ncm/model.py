from google.appengine.ext import db

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
        return name.replace(' ', '_')

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
    store_description = db.StringProperty(required=True)
    full_name = db.StringProperty(required=True)
    email = db.EmailProperty(required=True)
    paypal = db.EmailProperty()
    phone_number = db.PhoneNumberProperty(required=True)
    location = db.StringProperty(required=True)
    mailing_address = db.PostalAddressProperty(required=True)
    tags = db.CategoryProperty(required=True)
    
class Product(db.Model):
    """ Something a Maker can sell to a Shopper """
    maker = db.ReferenceProperty(Maker, collection_name='products')
    name = db.StringProperty(required=True)
    description = db.StringProperty(required=True)
    price = db.FloatProperty(required=True)
    tags = db.CategoryProperty(required=True)
    inventory = db.IntegerProperty(required=True)

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
        return title.replace(' ', '_')

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
