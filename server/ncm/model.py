from google.appengine.ext import db

class Maker(db.Model):
    """ Someone who sells products  """
    user = db.UserProperty()
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
    title = db.StringProperty()
    time = db.DateTimeProperty()
    text = db.TextProperty()
    show = db.BooleanProperty()

class EventNotice(db.Model):
    title = db.StringProperty()
    time = db.DateTimeProperty()
    text = db.TextProperty()
    show = db.BooleanProperty()
    
class TipItem(db.Model):
    title = db.StringProperty()
    text = db.TextProperty()
    show = db.BooleanProperty()
