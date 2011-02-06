from google.appengine.ext import db

class Community(db.Model):
    """ A Community of Makers and Crafters  """
    name = db.StringProperty(required=True)

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

class ProductImage(db.Model):
    """ An Image of a Product """
    product = db.ReferenceProperty(Product, collection_name='product_images')
    image = db.BlobProperty()

class ShoppingCartItem:
    def __init__(self, product = '', count = 0):
        self.product = product
        self.count = count

# Transactons represent a point in time, so they keep
# a copy of all the information they need.
# This needs more thought. Is there  transaction for an entire shopping
# cart and then a transaction for each Maker with a Product in the shopping
# cart or is there a transaction for each Product even? Maybe I need a 
# "Sale" entity that represents the sale of some number of an individual product.
#  Hmm and how to keys, paths and "parents" figure into this?
#
class Transaction(db.Model):
    """ Money changed hands. """
    amount = db.FloatProperty(required=True)
    timestamp = db.DateTimeProperty(auto_now_add=True)
    transaction_type = db.CategoryProperty(['Sale', 'Payout', 'Refund'])
    note = db.TextProperty()
    authorization = db.StringProperty()

# NewsItems, EventNotices and TipItems  are similar
# but they are never logically managed together
# so we don't bother with a PolyModel

class NewsItem(db.Model):
    """ Local news relevant to makers  """
    community = db.ReferenceProperty(Community, collection_name='community_news_items')
    title = db.StringProperty()
    time = db.DateTimeProperty()
    text = db.TextProperty()
    show = db.BooleanProperty()

class EventNotice(db.Model):
    """ A community event like a sack lunch or a meet and greet """
    community = db.ReferenceProperty(Community, collection_name='community_event_notice')
    title = db.StringProperty()
    time = db.DateTimeProperty()
    text = db.TextProperty()
    show = db.BooleanProperty()
    
class TipItem(db.Model):
    """ A hint or tip about how to use the site or a creative howto  """
    community = db.ReferenceProperty(Community, collection_name='community_tip_item')
    title = db.StringProperty()
    text = db.TextProperty()
    show = db.BooleanProperty()
