import requests as rq
import os
from cerberus import Validator
from raven import Client
from dotenv import load_dotenv
from openerp.osv import osv
load_dotenv()
client = Client(
    os.getenv('RAVEN_CLIENT'))
URL = os.getenv('URL')
INTERNAL_AUTHENTICATION_TOKEN = os.getenv('INTERNAL_AUTHENTICATION_TOKEN')
from requests.exceptions import ConnectionError


def postHome(data):
    if(validateHomeData(data)):
        try:
            return rq.post("{}/homes".format(URL), json=data, headers={'token': INTERNAL_AUTHENTICATION_TOKEN})
        except ConnectionError as err:
            message = 'Unable to establish connection to backend server'
            client.captureMessage(err)
            raise osv.except_osv(('Error!'), (message))
        except Exception as err:
            message = 'Something went wrong'
            client.captureMessage(err)
            raise osv.except_osv(('Error!'), (message))

def getHome(id):
    try:
        return rq.get(URL+"/homes?filter={}={}".format('odooID', id), headers={'token': INTERNAL_AUTHENTICATION_TOKEN})
    except ConnectionError as err:
        message = 'Unable to establish connection to backend server'
        client.captureMessage(err)
        raise osv.except_osv(('Error!'), (message))
    except Exception as err:
        message = 'Something went wrong'
        client.captureMessage(err)
        raise osv.except_osv(('Error!'), (message))


def updateHome(id, data):
    if(validateHomeData(data)):
        try:
            return rq.put("{}/homes/{}".format(URL, id), json=data, headers={'token': INTERNAL_AUTHENTICATION_TOKEN})
        except ConnectionError as err:
            message = 'Unable to establish connection to backend server'
            client.captureMessage(err)
            raise osv.except_osv(('Error!'), (message))
        except Exception as err:
            message = 'Something went wrong'
            client.captureMessage(err)
            raise osv.except_osv(('Error!'), (message))


def validateHomeData(data):
    v = Validator()
    schema = {
        'name': {'type': 'string', 'empty': False},  # map
        'role': {'type': 'string', 'allowed': ['home', 'company', 'organization']},
        'street': {'type': 'string', 'empty': False},
        'zip': {'type': 'string', 'empty': False},
        'city':  {'type': 'string', 'empty': False},
        'odooID': {'type': 'number'},
        'children': {'type': 'list'},
        'subscriptionEndDate': {'type': 'string'}
    }
    result = v.validate(data, schema)
    if(not result):
        raise osv.except_osv(
            ('Error!'), ('Address in missing'))
    return result
