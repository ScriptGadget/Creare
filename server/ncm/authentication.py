#  Copyright 2011 Bill Glover
#
#  This file is part of Creare.
#
#  Creare is free software: you can redistribute it and/or modify it
#  under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  Creare is distributed in the hope that it will be useful, but
#  WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with Creare.  If not, see <http://www.gnu.org/licenses/>.
#
import logging
from google.appengine.ext import webapp
from google.appengine.ext.webapp import util
from google.appengine.api import users
from google.appengine.ext import db

from model import *

class Authenticator:
    def __init__(self, page):
        self.page = page

    def authenticate(self):
        """ Ask a visitor to login before proceeding.  """
        user = users.get_current_user()
        maker = None

        if not user:
            self.page.redirect(users.create_login_url(self.page.request.uri))
            raise AuthenticationException('User must authenticate')
        else:
            maker = Maker.getMakerForUser(user)
        return (user, maker)

    @staticmethod
    def authorized_for(user):
        return user and user == users.get_current_user()
