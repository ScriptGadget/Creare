# !/usr/bin/env python
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
from model import *

def get_maker_with_products(makers):
    if makers:
        next_maker = None
        for maker in makers:
            product = Product.all(keys_only=True).filter('maker =', maker).filter('disable =', False).filter('show =', True).get()
            if product:
                next_maker = maker
                break
    return next_maker
        
community = Community.all().get()
current = None
if community.featured_maker:
    current = Maker.get(community.featured_maker)

next_maker = None
if current:
    makers = Maker.all(keys_only=True).order('joined').filter('joined >', current.joined).filter('approval_status =', 'Approved')
    next_maker = get_maker_with_products(makers)

if not next_maker:
    makers = Maker.all(keys_only=True).order('joined').filter('approval_status =', 'Approved')
    next_maker = get_maker_with_products(makers)

if next_maker:
    community.featured_maker = str(next_maker)
    community.put()
    
