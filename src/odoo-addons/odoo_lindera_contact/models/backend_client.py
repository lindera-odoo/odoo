from odoo import models, fields, api
import requests as rq
import os
from cerberus import Validator
from raven import Client
from openerp.osv import osv
from requests.exceptions import ConnectionError


class BackendClient():

    def __init__(self, url, token, ravenClient):
        self.URL = url
        self.INTERNAL_AUTHENTICATION_TOKEN = token
        self.client = Client(ravenClient)

    def postHome(self, data):
        if(self.validateHomeData(data)):
            try:
                return rq.post("{}/homes".format(self.URL), json=data, headers={'token': self.INTERNAL_AUTHENTICATION_TOKEN})
            except ConnectionError as err:
                message = 'Unable to establish connection to backend server'
                self.client.captureMessage(err)
                raise osv.except_osv(('Error!'), (message))
            except Exception as err:
                message = 'Something went wrong'
                self.client.captureMessage(err)
                raise osv.except_osv(('Error!'), (message))

    def getHome(self, id):
        try:
            return rq.get(self.URL+"/homes?filter={}={}".format('odooID', id), headers={'token': self.INTERNAL_AUTHENTICATION_TOKEN})
        except ConnectionError as err:
            message = 'Unable to establish connection to backend server'
            self.client.captureMessage(err)
            raise osv.except_osv(('Error!'), (message))
        except Exception as err:
            message = 'Something went wrong'
            self.client.captureMessage(err)
            raise osv.except_osv(('Error!'), (message))

    def updateHome(self, id, data):
        if(self.validateHomeData(data)):
            try:
                return rq.put("{}/homes/{}".format(self.URL, id), json=data, headers={'token': self.INTERNAL_AUTHENTICATION_TOKEN})
            except ConnectionError as err:
                message = 'Unable to establish connection to backend server'
                self.client.captureMessage(err)
                raise osv.except_osv(('Error!'), (message))
            except Exception as err:
                message = 'Something went wrong'
                self.client.captureMessage(err)
                raise osv.except_osv(('Error!'), (message))

    def validateHomeData(self, data):
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
