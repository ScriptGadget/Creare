import logging
import unittest
from google.appengine.ext import db
from model import Community, Maker

class TestCommunity(unittest.TestCase):
    """ Test the Maker model. """

    def setUp(self):
        """ Setup Tests """
        self.community = Community(
            name='Test Community',
            slug=Community.get_slug_for_name('Test_Community')
            )

        self.community.put()

        self.maker = Maker(community=self.community,
                           store_name="Test Store",
                           store_description='A test store',
                           full_name="Tina Test",
                           email='test@example.com',
                           paypal_business_account_email = "maker@gmail.com",
                           phone_number = "530111121",
                           location = "Right Here",
                           mailing_address = "111 Test Lane, Testable, CA 95945",
                           approval_status = 'Approved',
                           tags=['test', 'testy', 'testiferous'])
        self.maker.put()


    def tearDown(self):
        self.maker.delete()
        self.community.delete()

    def testEmailValidation(self):
        try:
            self.maker.paypal_business_account_email = "good@example.com"
            self.maker.put()
            self.maker.paypal_business_account_email = "good@example.co.uk"
            self.maker.put()
            self.maker.paypal_business_account_email = "good.to.go@example.com"
            self.maker.put()
            self.maker.paypal_business_account_email = "good_to_go@example-host.com"
            self.maker.put()
            self.maker.paypal_business_account_email = "a@b.co.uk"
            self.maker.put()
        except db.BadValueError:
            self.fail('Threw exception for good email address: ' + self.maker.paypal_business_account_email)

        try:
            self.maker.paypal_business_account_email = "thisshouldfail"
            self.maker.put()
            self.maker.paypal_business_account_email = "badexample.com"
            self.maker.put()            
            self.maker.paypal_business_account_email = "bad+email@example.com"
            self.maker.put()
            self.maker.paypal_business_account_email = "bad@example_host.com"
            self.maker.put()            
        except db.BadValueError:
            # We expect an exception, this is success
            return

        self.fail('Failed to throw exception for bad email address: ' + self.maker.paypal_business_account_email)
