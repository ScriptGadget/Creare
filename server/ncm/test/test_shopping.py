import unittest
import logging
from google.appengine.api import users
from model import *

class TestShopping(unittest.TestCase):
    """ Test buying Products from one or more Makers """

    def setUp(self):
        """ Setup Tests """
        # Need a community, six makers and about 10 products
        pass

    def tearDown(self):
        pass

    def testShoppingCartItem(self):
        """ Right now just a trivial placeholder test, but we will add more. """
        price = 2.2
        count = 12.2
        item = ShoppingCartItem(product_key='abcd1234', price=price, count=count)
        self.assertTrue(item.subtotal == price * count)

