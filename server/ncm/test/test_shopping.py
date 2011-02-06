import unittest
from google.appengine.api import users
from model import Maker, Product

class TestShopping(unittest.TestCase):
    """ Test buying Products from one or more Makers """

    def setUp(self):
        """ Setup Tests """
        self.maker = Maker(store_name='Craftorama',
              user = users.User('test@example.com'),
              store_description="The Crafty Crafter's Place",
              full_name="Maggie Crafter",
              email='maggie@example.com',
              paypal='paypal_maggie@domain.com',
              phone_number='1-800-555-1212',
              location='Corner of Mill and Main',
              mailing_address='111 Mill Street, Grass Valley, CA, 95945',
              tags='tchotckies, geegaws, jimcracks, cruelty free faux taxidermy')
        self.maker.put()

        self.geegaw = Product(name='geegaw', description='Regulation Red GeeGaw', price=9.95, tags='geegaw, red, regulation, squishy', maker=self.maker)
        self.geegaw.put()

        self.bunny = Product(name='Dust Bunny Plushy', description='Stuffed Dust Bunny', price=11.99, tags='plush, taxidermy, faux, cruelty free, cute', maker=self.maker)
        self.bunny.put()

    def tearDown(self):
        self.bunny.delete()
        self.geegaw.delete()
        self.maker.delete()

    def testPurchaseSingleProduct(self):
        self.fail('Not Yet Implemented')
