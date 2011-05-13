import unittest
import logging
from google.appengine.ext import db
from model import *
from payment import *

def withinDelta(x, y, d=0.005):
    return x - y < d and y - x < d

class TestShopping(unittest.TestCase):
    """ Test buying Products from one or more Makers """

    def setUp(self):
        """ Setup Tests """
        self.community = Community(name='Test Community',
                                   slug=Community.get_slug_for_name('Test_Community'),
                                   paypal_sandbox_business_id = 'market1@gmail.com',
                                   use_sandbox=True,
                                   fee_percentage=10.0,
                                   fee_minimum=0.3,
                                   paypal_fee_percentage=2.9,
                                   paypal_fee_minimum=0.3)
        self.community.put()
        self.makers = []
        for i in range(0,7):
            maker = Maker(community=self.community,
                          store_name="Test Store #%d" % i,
                          store_description='A test store',
                          full_name="Tina%d Test" % i,
                          email='test@example.com',
                          paypal_business_account_email = "maker%d@gmail.com" % i,
                          phone_number = "530111121%d" % i,
                          location = "Right Here",
                          mailing_address = "111 Test Lane, Testable, CA 95945",
                          approval_status = 'Approved',
                          tags=['test', 'testy', 'testiferous'])
            self.makers.append(maker)
        db.put(self.makers)

        self.products = []
        count = 0
        i = 0
        for price in [1.00, 2.00, 3.00, 4.00, 5.00, 6.00, 17.00, 18.00, 19.00]:
            self.products.append(Product(maker=self.makers[i],
                              name="Test Product #%d" % count,
                              short_description='A product for testing.',
                              description="Just a product for testing, OK?",
                              price=price,
                              tags=['stuff', 'things'],
                              inventory=1000))
            count += 1
            i += 1
            i %= (len(self.makers) - 1)
        db.put(self.products)

    def tearDown(self):
        db.delete(self.products)
        db.delete(self.makers)
        db.delete(self.community)

    def testShoppingCartItem(self):
        """ Right now just a trivial placeholder test, but we will add more. """
        price = 2.2
        count = 12.2
        item = ShoppingCartItem(product_key='abcd1234', price=price, count=count)
        self.assertTrue(withinDelta(item.subtotal, price * count))

    def testCreateReceiverList(self):
        cart_items = []
        for product in self.products:
            item = ShoppingCartItem(product_key=product.key(),
                                    count=1,
                                    price=product.price)
            cart_items.append(item)

        receivers = ShoppingCartItem.createReceiverList(community=self.community,
                                                        shopping_cart_items=cart_items)
        self.assertTrue('primary' in receivers)
        self.assertTrue('others' in receivers)

        (email, amount) = receivers['primary']
        self.assertTrue(email == self.community.paypal_sandbox_business_id)
        self.assertTrue(withinDelta(amount,75.00))

        others = receivers['others']
        others.sort()

        (email, amount) = others[0]
        self.assertTrue(email == 'maker0@gmail.com')
        self.assertTrue(withinDelta(amount, 15.08))

        (email, amount) = others[1]
        self.assertTrue(email == 'maker1@gmail.com')
        self.assertTrue(withinDelta(amount, 16.82 ))

        (email, amount) = others[2]
        self.assertTrue(email == 'maker2@gmail.com')
        self.assertTrue(withinDelta(amount, 18.56))

        (email, amount) = others[3]
        self.assertTrue(email == 'maker3@gmail.com')
        self.assertTrue(withinDelta(amount, 2.88))

        (email, amount) = others[4]
        self.assertTrue(email == 'maker4@gmail.com')
        self.assertTrue(withinDelta(amount, 3.76))

        (email, amount) = others[5]
        self.assertTrue(email == 'maker5@gmail.com')
        self.assertTrue(withinDelta(amount, 4.63))

    def testFindProductsByTag(self):
        """ Test searching for products with a single tag. """
        self.products[1].tags.append('grails')
        self.products[1].put()
        p = Product.findProductsByTag('grails')
        self.assertTrue(p is not None)
        result = p.fetch(10)
        self.assertTrue(len(result) == 1)
        self.assertTrue(result[0].key() == self.products[1].key())

    def testProductSearch(self):
        """ Test searching for products by multiple tags. """
        self.products[1].tags.append('grails')
        self.products[1].put()
        self.products[2].tags.append('parrot')
        self.products[2].put()
        self.products[3].tags.append('parrot')
        self.products[3].tags.append('grails')
        self.products[3].put()
        result = Product.searchByTag('grails parrot')
        self.assertTrue(result is not None)
        self.assertTrue(len(result) == 3)
        for product in result:
            self.assertTrue(product.key() == self.products[1].key()
                            or product.key() == self.products[2].key()
                            or product.key() == self.products[3].key())
