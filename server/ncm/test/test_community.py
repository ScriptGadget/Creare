import logging
import unittest
from google.appengine.api import memcache
from model import Community, Advertisement

class TestCommunity(unittest.TestCase):
    """ Test the Community model. """

    def setUp(self):
        """ Setup Tests """
        self.community = Community(name='Test Community',
                                   slug=Community.get_slug_for_name('Test_Community'),
                                   use_sandbox=True,
                                   fee_percentage=10.0,
                                   fee_minimum=0.3,
                                   paypal_fee_percentage=2.9,
                                   paypal_fee_minimum=0.3,
                                   paypal_sandbox_business_id = 'sand_market1_biz@gmail.com',
                                   paypal_sandbox_email_address = 'sand_market1@gmail.com',
                                   paypal_sandbox_api_username = 'sand_api_user',
                                   paypal_sandbox_api_password = 'sand_api_pass',
                                   paypal_sandbox_api_signature = 'sand_api_sig',
                                   paypal_sandbox_application_id = 'sand_api_app_id',
                                   paypal_business_id = 'market1_biz@gmail.com',
                                   paypal_email_address = 'market1@gmail.com',
                                   paypal_api_username = 'api_user',
                                   paypal_api_password = 'api_pass',
                                   paypal_api_signature = 'api_sig',
                                   paypal_application_id = 'api_app_id',
                                   )
        self.community.put()

    def tearDown(self):
        memcache.flush_all()
        self.community.delete()

    def testSlugs(self):
        name = 'name with a space'
        slug = Community.get_slug_for_name(name)
        self.assertTrue(slug == 'name-with-a-space')

    def testAdImpressions(self):
        advertisement = Advertisement(name='Test')
        advertisement.put()
        self.assertTrue(advertisement.remaining_impressions() == 0)
        advertisement.refill_impressions(10000)
        self.assertTrue(advertisement.remaining_impressions() == 10000)
        advertisement.decrement_impressions()
        advertisement.decrement_impressions()
        self.assertTrue(advertisement.remaining_impressions() == 9998)

    def testCredentials(self):
        self.community.use_sandbox = True
        self.assertTrue(self.community.business_id == self.community.paypal_sandbox_business_id)
        self.assertTrue(self.community.email_address == self.community.paypal_sandbox_email_address)
        self.assertTrue(self.community.api_username == self.community.paypal_sandbox_api_username)
        self.assertTrue(self.community.api_password == self.community.paypal_sandbox_api_password)
        self.assertTrue(self.community.api_signature == self.community.paypal_sandbox_api_signature)
        self.assertTrue(self.community.application_id == self.community.paypal_sandbox_application_id)

        self.community.use_sandbox = False
        self.assertTrue(self.community.business_id == self.community.paypal_business_id)
        self.assertTrue(self.community.email_address == self.community.paypal_email_address)
        self.assertTrue(self.community.api_username == self.community.paypal_api_username)
        self.assertTrue(self.community.api_password == self.community.paypal_api_password)
        self.assertTrue(self.community.api_signature == self.community.paypal_api_signature)
        self.assertTrue(self.community.application_id == self.community.paypal_application_id)
