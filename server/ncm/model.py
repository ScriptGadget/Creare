from google.appengine.ext import db

class Shopper(db.Model):
    """ Someone who can buy products  """
    user_id = db.StringProperty()
    name = db.StringProperty()
    email = db.EmailProperty()

class Maker(db.Model):
    """ Someone who sells products  """
    user = db.UserProperty()
    store_name = db.StringProperty()
    store_description = db.StringProperty()
    full_name = db.StringProperty()
    email = db.EmailProperty()
    paypal = db.EmailProperty()
    phone_number = db.PhoneNumberProperty()
    location = db.StringProperty()
    mailing_address = db.PostalAddressProperty()
    tags = db.CategoryProperty()
    
class Product(db.Model):
    """ Something a Maker can sell to a Shopper """
    description = db.StringProperty()
    price = db.FloatProperty()
    tags = db.CategoryProperty()
    # maker = db.ReferenceProperty(Maker, collection_name='products')
