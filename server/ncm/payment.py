import logging
from cgi import parse_qs
from google.appengine.ext import webapp
from google.appengine.ext import db
import urllib
from google.appengine.api import urlfetch

class PaypalPaymentResponse(db.Model):
    """ parent will be a CartTransaction """
    response=db.TextProperty(required=True)
    timestamp = db.DateTimeProperty(auto_now_add=True)

class PaypalExpressCheckoutButton:
    """ A simple unencrypted Paypal Express Checkout form generator. """    
    def __init__(self):
        self.button_img =  """<img src="https://www.paypal.com/en_US/i/btn/btn_xpressCheckout.gif" align="left" style="margin-right:7px;">"""

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
    This is for paying Makers and not for receiving money from customers. This should probably be parallell or batch payments instead.
    """
    def __init__(self, primary_recipient, additional_recipients, api_username, api_password, 
                 api_signature, application_id, client_ip, cancel_url, return_url, action_url, 
                 sandbox_email=""):
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

        if action_url.count('sandbox') > 0:
            self.headers['X-PAYPAL-SANDBOX-EMAIL-ADDRESS']=sandbox_email
            self.redirect_url_template = 'https://sandbox.paypal.com/webscr?cmd=_ap-payment&paykey='
        else:
            self.redirect_url_template = 'https://www.paypal.com/webscr?cmd=_ap-payment&paykey='

        self.form_fields = []
        self.form_fields.append(('actionType','PAY'))
        self.form_fields.append(('cancelUrl', cancel_url))

        #By convention, we will always put the primary first.
        (email, amount) = primary_recipient
        self.form_fields.append(('receiverList.receiver(0).email', email))
        self.form_fields.append(('receiverList.receiver(0).amount',  '%.2f' % amount))
        self.form_fields.append(('receiverList.receiver(0).primary', 'true'))

        i = 1
        for recipient in additional_recipients:
            (email, amount) = recipient
            self.form_fields.append(("receiverList.receiver(%d).email" % i, email))
            self.form_fields.append(("receiverList.receiver(%d).amount" % i, '%.2f' % amount))
            i += 1

        self.form_fields.append(('returnUrl', return_url))
        self.form_fields.append(('currencyCode', 'USD'))
        self.form_fields.append(('requestEnvelope.errorLanguage', 'en_US'))

    def buildRedirectURL(self, response, sandbox=False):
        url = None
        parsed_response = parse_qs(response.content)
        try:
            ack = parsed_response['responseEnvelope.ack'][0]
            if ack and ack == 'Success':
                url = self.redirect_url_template + parsed_response['payKey'][0]

        except KeyError:
            logging.error('Bad Response from PayPal: %s\n' % response.content)

        return url

    def execute(self):
        result = None
        try:
            form_data = urllib.urlencode(self.form_fields)
            logging.info(form_data)
            response = urlfetch.fetch(url=self.action_url,
                                    payload=form_data,
                                    method=urlfetch.POST,
                                    headers=self.headers)

        except Exception as e:
            logging.error("PaypalChainedPayment.execute(): Unexpected Exception %s\n" % str(e))

        if not response:
            logging.error("PaypalChainedPayment.execute(): No Response from Paypal \n")
        if response.status_code != 200:
            logging.error("PaypalChainedPayment.execute(): Unexpected HTTP Error %d\n" % response.status_code)
        else:
            logging.info("PaypalChainedPayment.execute(): response = %s\n" % str(response.content));
            logging.info("redirect: %s\n" % self.buildRedirectURL(response))

        return response
