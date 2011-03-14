import logging
import unittest
from google.appengine.ext import db
from model import *
from ipn import *

class TestSandboxPayment(unittest.TestCase):
    """ Test payment (currently only via Paypal) """

    def setUp(self):
        self.cart = CartTransaction ( paypal_pay_key='test_key' )
        self.cart.put()
        
        self.products = []

        self.makers = []
        self.products = []
        self.maker_transactions = []

        for i in range(5):
            maker = Maker(
                store_name='Test Store #%d' % i,
                store_description = 'Nothing',
                full_name = 'Maker %d' % i,
                email = 'maker%d@example.com' % i,
                paypal_business_account_email = 'maker%d_5551212_biz@gmail.com' %i,
                phone_number = '5305551212',
                location = 'Test Place',
                mailing_address = '111 Test Ave, Tester CA, 95945',
                tags = 'tests, testing, stuff to test',
                )
            maker.put()
            self.makers.append(maker)

            product = Product(
                maker=maker,
                name="%s's Product" % maker.full_name,
                short_description="Product #%d" % i,
                description="Yes it is Product #%d!" % i,
                price=9.95,
                tags="Test, Item",
                inventory=10 
                )
            product.put()
            self.products.append(product)

            entry = "%s:%s:%s" % (str(product.key()),
                                  str(i+1),
                                  "%.2f" %product.price)

            transaction = MakerTransaction(
                parent=self.cart,
                maker=maker,
                email=maker.paypal_business_account_email,
                when='now-ish%d' % i,
                detail=[entry],
                )
            transaction.put()
            self.maker_transactions.append(transaction)
        
    def tearDown(self):
        self.cart.delete()
        db.delete(self.maker_transactions)
        db.delete(self.makers)

    def test_update_cart_and_maker_transaction_record_COMPLETED(self):
        parameters = {
            'pay_key':'test_key',
            'trackingId':self.cart.key(),
            }

        # The PP_AdaptivePayments.book manual claims this should be "SUCCESS"
        # But in the sandbox at least this come back as "Completed"
        for i in range(5):
            parameters['transaction[%d].status_for_sender_txn' % i] = 'Completed'
            parameters['transaction[%d].receiver' % i] = self.makers[i].paypal_business_account_email

        status = 'COMPLETED'
        
        IPNHandler.update_inventory(self.cart, status, parameters)

        cart = CartTransaction.get(self.cart.key())
        self.assertTrue(cart.transaction_status == status)
        
        t = MakerTransaction.all()
        t.ancestor(cart)
        maker_transactions = t.fetch(5)
        for transaction in maker_transactions:
            self.assertTrue(transaction.status == 'Paid')

            for entry in transaction.detail:
                (product_key, items, amount) = entry.split(':')
                count = int(items)
                product = Product.get(product_key)
                self.assertTrue(product is not None)
                logging.info("product.inventory: %d count: %d" % (product.inventory, count));
                self.assertTrue(product.inventory == 10-count)

    def test_update_cart_and_maker_transaction_record_ERROR(self):
        parameters = {
            'pay_key':'test_key',
            'trackingId':self.cart.key(),
            }

        for i in range(5):
            parameters['transaction[%d].status_for_sender_txn' % i] = 'FAILURE'
            parameters['transaction[%d].receiver' % i] = self.makers[i].paypal_business_account_email

        status = 'ERROR'

        IPNHandler.update_inventory(self.cart, status, parameters)

        cart = CartTransaction.get(self.cart.key())
        self.assertTrue(cart.transaction_status == status)
        
        q = MakerTransaction.all()
        q.ancestor(cart)
        maker_transactions = q.fetch(5)
        for transaction in maker_transactions:
            self.assertTrue(transaction.status == 'Error')
            for entry in transaction.detail:
                (product_key, items, amount) = entry.split(':')
                product = Product.get(product_key)
                self.assertTrue(product is not None)
                self.assertTrue(product.inventory == 10)
