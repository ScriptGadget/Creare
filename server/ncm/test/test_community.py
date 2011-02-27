import unittest
from google.appengine.api import users
from model import Community

class TestCommunity(unittest.TestCase):
    """ Test the Community model. """

    def setUp(self):
        """ Setup Tests """
        pass

    def tearDown(self):
        pass

    def testSlugs(self):
        name = 'name with a space'
        slug = Community.get_slug_for_name(name)
        self.assertTrue(slug == 'name-with-a-space')
