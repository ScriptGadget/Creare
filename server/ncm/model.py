from google.appengine.ext import db
from google.appengine.ext.db import polymodel

class Maker(db.Model):
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
    description = db.StringProperty()
    price = db.FloatProperty()
    tags = db.CategoryProperty()
    maker = db.ReferenceProperty(Maker, collection_name='products')

m = Maker(store_name='Craftorama',
          store_description="The Crafty Crafter's Place",
          full_name="Maggie Crafter",
          email='maggie@domain.com',
          paypal='paypal_maggie@domain.com',
          phone_number='1-800-555-1212',
          location='Corner of Mill and Main',
          mailing_address='111 Mill Street, Grass Valley, CA, 95945',
          tags='tchotckies, geegaws, jimcracks, cruelty free faux taxidermy')
m.put()

p = Product(description='Regulation Red GeeGaw', price=9.95, tags='geegaw, red, regulation, squishy', maker=m)

p.put()

p = Product(description='Blue Sequined GeeGaw', price=22.87, tags='blue, sequined, geegaw, antique', maker=m)

p.put()

p = Product(description='Stuffed Dust Bunny', price=11.99, tags='plush, taxidermy, faux, cruelty free, cute', maker=m)

p.put()

