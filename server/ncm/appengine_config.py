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
#  This is a setup file needed by gaesessions (gaesessions itself
#  is not part of Creare). This should probably be removed from
#  the repository and replaced with instructions on where to get
#  gaesessions and instruction for how to instal it.

from gaesessions import SessionMiddleware
def webapp_add_wsgi_middleware(app):
    app = SessionMiddleware(app, cookie_key='KMOPgO79WHQ4vtrUil9TPPPK33idCJaHi+FL/O+v34cri8CQ5N9aPOgO1xjWYwVp7HS8js1Rx0YW2i9C4CbT3Q==')
    return app
