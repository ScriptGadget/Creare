import logging
from google.appengine.ext import webapp
from google.appengine.ext import db
import urllib
from google.appengine.api import urlfetch

class PaypalPaymentResponse(db.Model):
    """ parent will be a CartTransaction """
    response=db.StringProperty(required=True)
    timestamp = db.DateTimeProperty(auto_now_add=True)

class PaypalButton:
    """ A simple unencrypted paypal button form generator.  """

    def __init__(self, paypal_id, return_url, cancel_url, tax_rate, sandbox=False):
        self.paypal_id = paypal_id
        self.return_url = return_url
        self.cancel_url = cancel_url
        self.tax_rate = tax_rate
        if sandbox:
            self.action_url = "https://www.sandbox.paypal.com/cgi-bin/webscr"
        else:
            self.action_url = "https://www.paypal.com/cgi-bin/webscr"

    def content(self, item_name, item_number, amount, transaction_id):
        """ Create the form content. A PaypalButton object can be reused this way
        for multiple items. """
        pass
        """
        button =
        <form action="{action_url}" method="post">
        <input type="hidden" name="cmd" value="_xclick">
        <input type="hidden" name="business" value="{paypal_id}">
        <input type="hidden" name="lc" value="US">
        <input type="hidden" name="item_name" value="{item_name}">
        <input type="hidden" name="item_number" value="{item_number}">
        <input type="hidden" name="amount" value="{amount}">
        <input type="hidden" name="currency_code" value="USD">
        <input type="hidden" name="button_subtype" value="services">
        <input type="hidden" name="no_note" value="0">
        <input type="hidden" name="cn" value="Add special instructions to the seller">
        <input type="hidden" name="no_shipping" value="2">
        <input type="hidden" name="rm" value="1">
        <input type="hidden" name="return" value="{return_url}">
        <input type="hidden" name="cancel_return" value="{cancel_url}">
        <input type="hidden" name="tax_rate" value="{tax_rate}">
        <input type="hidden" name="bn" value="PP-BuyNowBF:btn_buynow_SM.gif:NonHosted">
        <input type="hidden" name="transaction_id" value="{transaction_id}">
        <input type="image" src="https://www.paypal.com/en_US/i/btn/btn_buynow_SM.gif" border="0" name="submit" alt="PayPal - The safer, easier way to pay online!">
        <img alt="" border="0" src="https://www.paypal.com/en_US/i/scr/pixel.gif" width="1" height="1">
        </form>
        % ('action_url':self.action_url,
               'paypal_id':self.paypal_id,
               'return_url':self.return_url,
               'cancel_url':self.cancel_url,
               'tax_rate':self. tax_rate,
               'item_name':item_name,
               'item_number':item_number,
               'amount':amount,
               'transaction_id':transaction_id, )
        return button
        """

class PaypalIPHandler:
    """ 
    A minimal handler for receiving and validating IPN messages. 
    """
    pass

class TooManyRecipientsException (Exception):

    def __init_(self, number):
        self.number = number;

    def __str__(self):
        return 'Paypal only allows 5 additional recipients. This Payment requests: ' + repr(self.number)

class PaypalChainedPayment:
    """ 
    Knows how to make a single chained payment and fetch an approval URL. 
    Create a new instance each shopping cart checkout.
    """
    def __init__(self, primary_recipient, additional_recipients, api_username, api_password, api_signature, application_id, client_ip, cancel_url, return_url, action_url):
        """
        Must have at least a primary receiver, additional receivers are optional. 
        Paypal does not currently support chained payments with more than five additional receivers.
        Throws a TooManyRecipientsException for len(additional_recipients) > 5
        """
        if(len(additional_recipients) > 5):
            raise TooManyRecipientsException(len(additional_recipients))
        self.action_url = action_url

        self.headers = {
                'Content-Type': 'application/x-www-form-urlencoded',
                'X-PAYPAL-SECURITY-USERID': api_username,
                'X-PAYPAL-SECURITY-PASSWORD': api_password,
                'X-PAYPAL-SECURITY-SIGNATURE': api_signature,
                'X-PAYPAL-REQUEST-DATA-FORMAT': 'NV',
                'X-PAYPAL-RESPONSE-DATA-FORMAT': 'NV',
                'X-PAYPAL-APPLICATION-ID': application_id,
                'X-PAYPAL-DEVICE-IPADDRESS': client_ip,
                }

        self.form_fields = {
            'actionType':'PAY',
            'cancelURL':cancel_url,
            'returnURL':return_url,
            'currencyCode':'USD',
            'requestEnvelope.errorLanguage':'en_US',            
            }

        #By convention, we will always put the primary first.
        (email, amount) = primary_recipient
        self.form_fields['receiver(0).email'] = email
        self.form_fields['receiver(0).amount'] = amount
        self.form_fields['receiver(0).primary'] = 'true'

        i = 1
        for recipient in additional_recipients:
            (email, amount) = recipient
            self.form_fields["receiver(%d).email" % i] = email
            self.form_fields["receiver(%d).amount" % i] = amount
            self.form_fields["receiver(%d).primary" % i] = 'false'
            i += 1
        logging.info("PaypalChainedPayment: %s %s\n" % (str(self.headers), str(self.form_fields)))
        return

    def execute(self):
        result = None
        try:
            form_data = urllib.urlencode(self.form_fields)        
            result = urlfetch.fetch(url=self.action_url,
                                    payload=form_data,
                                    method=urlfetch.POST,
                                    headers=self.headers)
        except Exception as e:
            logging.error("PaypalChainedPayment.execute(): Unexpected Exception %s\n" % str(e))

        if not result:
            logging.error("PaypalChainedPayment.execute(): No Response from Paypal \n")
        if result.status_code != 200:
               logging.error("PaypalChainedPayment.execute(): Unexpected HTTP Error %d\n" % result.status_code)
        else:
            logging.info("PaypalChainedPayment.execute(): result = %s\n" % str(result.content));

        return result
    
