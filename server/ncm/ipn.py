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
# A simple PayPal IPN Handler
# modified to handle chained payments
# Based in part on an example by George Kyaw Kyaw Naing at http://learnbysoft.blogspot.com/2010/09/paypal-ipn-google-app-engine-python.html
# which is, in turn, based on an example by Paul Kenjora at http://blog.awarelabs.com/2008/paypal-ipn-python-code

import logging
import urllib
from google.appengine.ext import webapp
from google.appengine.ext.webapp import util
from google.appengine.ext import db
from model import *
from payment import *

class IPNHandler(webapp.RequestHandler):
    """ Handle Paypal IPN updates """

    @staticmethod
    def update_cart_and_maker_transaction_record(cart_key, status, parameters):
        """ We got paid or had an error make a note of it."""
        cart = CartTransaction.get(cart_key)
        cart.transaction_status=status
        cart.put()

        q = MakerTransaction.all()
        q.ancestor(cart)
        maker_transactions = q.fetch(6) # This can't be more than five according to paypal. Should it be a constant someplace?
        num_maker_transactions = len(maker_transactions) # we should only get back as many as we sent

        maker_transaction_dict = {}
        for m in maker_transactions:
            maker_transaction_dict[m.email] = m

        i = 0
        while "transaction[%d].receiver" % i in parameters:
            maker_email = parameters["transaction[%d].receiver" % i]
            maker_status = parameters["transaction[%d].status_for_sender_txn" % i]
            if maker_email and maker_status and maker_email in maker_transaction_dict:
                m = maker_transaction_dict[maker_email]
                if maker_status == 'SUCCESS' or maker_status == 'Completed': # The docs say SUCCESS, the log says Completed
                    m.status = 'Paid'
                elif maker_status == 'PENDING' or maker_status == 'CREATED' or maker_status == 'PROCESSING':
                    m.status = 'Pending'
                    m.messages = maker_status
                else:
                    m.status = 'Error'
                    m.messages = maker_status
                m.put()
            i += 1

    @staticmethod
    def update_inventory(cart, status, parameters):
        db.run_in_transaction(IPNHandler.update_cart_and_maker_transaction_record, cart.key(), status, parameters)
    
        # We have just touched the MakerTransactions above. Is there
        # a way to just do this all once?
        if status == 'COMPLETED':
            transactions = MakerTransaction.all()
            transactions.ancestor(cart)
            for transaction in transactions:
                for entry in transaction.detail:
                    entry_fields = entry.split(':')
                    if len(entry_fields) == 4:
                        (product_key, items, amount, shipping) = entry_fields
                    else:
                        (product_key, items, amount) = entry_fields
                    count = int(items)
                    product = Product.get(product_key)                        
                    db.run_in_transaction( Product.decrement_product_inventory, product.key(), count )


    def ipn(self):
        """ Handle IPN updates. """
        community = Community.all().get()
        if not community:
            self.error(500)
            logging.error('Failed to find Community while receiving a Paypal IPN: '+ str(self.request))
            self.response.out.write("System not configured for Paypal IPN")
            return

        if community.use_sandbox:
            verification_url = SANDBOX_PP_URL
            our_email = community.paypal_sandbox_email_address
        else:
            verification_url = PP_URL
            our_email = community.paypal_email_address

        parameters = None

        status = self.request.get('status')
        
        if status == 'PENDING' or status == 'PROCESSING' or status == 'CREATED':
            self.response.out.write('OK') # Nothing for us to do
            return

        if self.request.POST:
            parameters = self.request.POST.copy()
        if self.request.GET:
            parameters = self.request.GET.copy()

        # Check the IPN POST request came from real PayPal, 
        # not from a fraudster.
        if parameters:
            parameters['cmd']='_notify-validate'
            params = urllib.urlencode(parameters)
            verification_status = urlfetch.fetch(
                url = verification_url,
                method = urlfetch.POST,  
                payload = params,
                ).content

            if not verification_status == "VERIFIED":
                self.response.out.write('Error. The request could not be verified, check for fraud.')
                logging.error('UNVERIFIED IPN: ' + str(self.request));
                return

            if status == 'INCOMPLETE' or status == 'ERROR' or status == 'REVERSALERROR':
                logging.error('ERROR: %s status reported by Paypal in IPN: request=%s' (status, str(self.request)))
            elif status == 'COMPLETED':
                # TBD
                # much error handling and fraud checking
                # email address, amounts, currency etc.
                # sender_email = parameters['sender_email']

                pay_key = parameters['pay_key']
                q = CartTransaction.all()
                q.filter('paypal_pay_key =', pay_key)
                cart = q.get()
                if not cart:
                    logging.error('Unrecognized IPN: ' + pay_key + ': ' + (self.request))
                    return
                else:
                    paypalPaymentResponse = PaypalPaymentResponse( parent=cart,
                                                               response=str(parameters))
                    paypalPaymentResponse.put();                    
                    IPNHandler.update_inventory(cart, status, parameters)
                    community.decrement_pending_score()


    def post(self):
        self.ipn()

    def get(self):
        self.ipn()

class NotFoundErrorHandler(webapp.RequestHandler):
    """ A site root page """
    def handle(self):
        self.error(404)
        self.response.out.write("Opps, that doesn't seem to be a valid page.")

    def get(self):
        self.handle()

    def post(self):
        self.handle()

def main():
    app = webapp.WSGIApplication([
        ('/ipn', IPNHandler),
        (r'.*', NotFoundErrorHandler),
        ])
    util.run_wsgi_app(app)

if __name__ == '__main__':
    main()
