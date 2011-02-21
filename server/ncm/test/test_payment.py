import unittest
from google.appengine.api import users
from payment import *

class TestPayment(unittest.TestCase):
    """ Test payment (currently only via Paypal) """

    def setUp(self):
        """ Setup Tests """
        pass

    def tearDown(self):
        pass

    def testDummyChainedPayment(self):
        amounts = [1.00,2.00,3.00,4.00,5.00]
        fee = 0.50
        num_recipients = len(amounts)
        others = []

        for i in range(num_recipients):
            others.append(("test%d@example.com" % (i+1), amounts[i]))

        try:
            payment = PaypalChainedPayment(
                primary_recipient=('test@example.com', fee),
                additional_recipients=others,
                api_username='test@example.com',
                api_password='fake_pass',
                api_signature='fake_sig',
                application_id='fake_id',
                client_ip='127.0.0.1',
                cancel_url='http://example.com/cancel',
                return_url='http://example.com/return',
                action_url='http://notreally.sandbox.paypal.com',
                )

        except TooManyRecipientsException:
            self.fail('Unexpected TooManyRecipientsException')

    def testChainedPaymentWithTooManyRecipients(self):
        total = 3.50
        fee = 0.50
        net = total-fee
        num_recipients = 6
        too_many = []

        for i in range(1, num_recipients+1):
            too_many.append(("test%d@example.com" % i, net/num_recipients))

        exceptionThrown = False
        try:
            payment = PaypalChainedPayment(
                primary_recipient=('test@example.com', fee),
                additional_recipients=too_many,
                api_username='test@example.com',
                api_password='fake_pass',
                api_signature='fake_sig',
                application_id='fake_id',
                client_ip='127.0.0.1',
                cancel_url='http://example.com/cancel',
                return_url='http://example.com/return',
                action_url='http://notreally.sandbox.paypal.com',
                )

        except TooManyRecipientsException:
            exceptionThrown = True;

        self.assertTrue(exceptionThrown)
            
