import unittest
import logging
from google.appengine.ext import db
from model import *
import ncm

class TestRPCHandlers(unittest.TestCase):
    """ Test RPC call handlers. """

    def setUp(self):
        self.cartTransaction = CartTransaction(
            transaction_status='COMPLETED',
            shopper_name='Shopper Zero',
            shopper_email='shopper@gmail.com',
            shopper_shipping='I can pick it up Tuesday'            
            )
        self.cartTransaction.put()

        self.community = Community(name='Test Community',
                                   slug=Community.get_slug_for_name('Test_Community'),
                                   paypal_sandbox_business_id = 'market1@gmail.com',
                                   use_sandbox=True,
                                   fee_percentage=10.0,
                                   fee_minimum=0.3,
                                   paypal_fee_percentage=2.9,
                                   paypal_fee_minimum=0.3)
        self.community.put()

        self.maker = Maker(community=self.community,
                           store_name="Test Store #0",
                           store_description='A test store',
                           full_name="Tina0 Test",
                           email='test@example.com',
                           paypal_business_account_email = "maker0@gmail.com",
                           phone_number = "5301111210",
                           location = "Right Here",
                           mailing_address = "111 Test Lane, Testable, CA 95945",
                           tags=['test', 'testy', 'testiferous'])
        self.maker.put()

        self.products = []
        count = 0
        for price in [6.50, 6.50, 6.50, 6.50]:
            self.products.append(
                Product(
                    maker=self.maker,
                    name="Test Product #%d" % count,
                    short_description='A product for testing.',
                    description="Just a product for testing, OK?",
                    price=price,
                    tags=['stuff', 'things'],
                    inventory=1000,
                    ))
            count += 1
        db.put(self.products)

        details = []
        for product in self.products:
            details.append(str(product.key()) + ':' + '1' + ':%02f' % product.price)

        self.makerTransaction = MakerTransaction(
            parent=self.cartTransaction,
            maker=self.maker,
            email=self.maker.email,
            detail=details,
            shipped=False,
            when='1',
            status='Paid',
            )
        self.makerTransaction.put()

    def tearDown(self):
        self.makerTransaction.delete()
        self.maker.delete()
        self.community.delete()
        self.cartTransaction.delete()

    def test_buildTransactionRow(self):
        """ 
        Test a helper method for the activity table. 
        This test was prompted by a bug in the display where I was adding
        the minimum fee for each product instead of once for the transaction.
        """
        fee_percentage = (self.community.paypal_fee_percentage + self.community.fee_percentage)*0.01
        logging.info(str(fee_percentage))
        fee_minimum = self.community.paypal_fee_minimum + self.community.fee_minimum
        logging.info(str(fee_minimum))
        (sale, additional_items, additional_sales) = ncm._buildTransactionRow(self.makerTransaction, fee_percentage, fee_minimum)
        self.assertTrue(additional_items == 4)
        self.assertTrue(additional_sales == 26.00)
        self.assertTrue(sale['amount'] == '26.00')
        self.assertTrue(sale['fee'] == '3.95')
        self.assertTrue(sale['net'] == '22.05')
