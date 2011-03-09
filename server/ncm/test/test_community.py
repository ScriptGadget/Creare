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
                                   paypal_sandbox_business_id = 'market1@gmail.com',
                                   use_sandbox=True,
                                   fee_percentage=10.0,
                                   fee_minimum=0.3,
                                   paypal_fee_percentage=2.9,
                                   paypal_fee_minimum=0.3)
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

