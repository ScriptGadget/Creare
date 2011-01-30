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
    name = db.StringProperty(required=True)
    description = db.StringProperty(required=True)
    price = db.FloatProperty(required=True)
    tags = db.CategoryProperty(required=True)
    # maker = db.ReferenceProperty(Maker, collection_name='products')
