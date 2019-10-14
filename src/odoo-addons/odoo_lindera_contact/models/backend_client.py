import requests as rq
import os
from cerberus import Validator
from raven import Client
from openerp.osv import osv

client = Client('https://2f93ec8aba4c419a836337bd8ff4b427:53d79797dd0642218c08b664581e4e6d@sentry.lindera.de/6')
URL = 'https://backend-testing.lindera.de/v2'
INTERNAL_AUTHENTICATION_TOKEN = 'Bearer HfpWLjqt5k0YqIjPgYtb'


def postHome(data):
    if(validateHomeData(data)):
        try:
            return rq.post("{}/homes".format(URL), json=data, headers={'token': INTERNAL_AUTHENTICATION_TOKEN})
        except:
            message = 'Lindera backend failed to create the resource (home)'
            client.captureMessage(message)
            raise osv.except_osv(('Error!'), (message))


def getHome(id):
    try:
        return rq.get(URL+"/homes?filter={}={}".format('odooID', id), headers={'token': INTERNAL_AUTHENTICATION_TOKEN})
    except:
        message = 'Lindera backend failed to fetch the resource (home)'

        client.captureMessage(message)
        raise osv.except_osv(('Error!'), (message))


def updateHome(id, data):
    if(validateHomeData(data)):
        try:
            return rq.put("{}/homes/{}".format(URL, id), json=data, headers={'token': INTERNAL_AUTHENTICATION_TOKEN})
        except:
            message = 'Lindera backend failed to update the resource (home)'
            client.captureMessage(message)
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
        'children': {'type': 'list'}
    }
    result = v.validate(data, schema)
    if(not result):
        raise osv.except_osv(
            ('Error!'), ('Invalid input data'))
    return result
