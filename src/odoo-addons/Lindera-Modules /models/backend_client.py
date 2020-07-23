from odoo import models, fields, api
import requests as rq
import os
from cerberus import Validator
from .ravenSingleton import ravenSingleton
from dotenv import load_dotenv
from openerp.osv import osv
from requests.exceptions import ConnectionError


class BackendClient():

    def __init__(self, url, token, ravenClient):
        self.URL = url
        self.INTERNAL_AUTHENTICATION_TOKEN = token
        self.ravenSingleton = ravenSingleton(ravenClient)

    @classmethod
    def setupBackendClient(cls, context):
        url = context.env['ir.config_parameter'].get_param('lindera.backend')
        token = context.env['ir.config_parameter'].get_param(
            'lindera.internal_authentication_token')
        ravenClient = context.env['ir.config_parameter'].get_param(
            'lindera.raven_client')

        if (url and token and ravenClient):
            return cls(
                url, token, ravenClient)
        else:
            raise osv.except_osv(
                ('Error!'), ('Please, setup system parameters for lindera backend'))

    def notifyBackendToCreateReport(self, data):
        try:
            return rq.post("{}/internal/create_report".format(self.URL), json=data, headers={'token': self.INTERNAL_AUTHENTICATION_TOKEN})
        except ConnectionError as err:
            message = 'Unable to establish connection to backend server'
            self.ravenSingleton.Client.captureMessage(err)
            raise osv.except_osv(('Error!'), (message))
        except Exception as err:
            self.ravenSingleton.Client.captureMessage(err)
            raise osv.except_osv(('Error!'), (self.URL, err))

    def postHome(self, data):
        if(self.validateHomeData(data)):
            try:
                return rq.post("{}/homes".format(self.URL), json=data, headers={'token': self.INTERNAL_AUTHENTICATION_TOKEN})
            except ConnectionError as err:
                message = 'Unable to establish connection to backend server'
                self.ravenSingleton.Client.captureMessage(err)
                raise osv.except_osv(('Error!'), (message))
            except Exception as err:
                self.ravenSingleton.Client.captureMessage(err)
                raise osv.except_osv(('Error!'), (self.URL, err))

    def getHome(self, id):
        try:
            return rq.get(self.URL+"/homes?filter={}={}".format('odooID', id), headers={'token': self.INTERNAL_AUTHENTICATION_TOKEN})
        except ConnectionError as err:
            message = 'Unable to establish connection to backend server'
            self.ravenSingleton.Client.captureMessage(err)
            raise osv.except_osv(('Error!'), (message))
        except Exception as err:
            message = 'Something went wrong'
            self.ravenSingleton.Client.captureMessage(err)
            raise osv.except_osv(('Error!'), (message))

    def updateHome(self, id, data):
        if(self.validateHomeData(data)):
            try:
                return rq.put("{}/homes/{}".format(self.URL, id), json=data, headers={'token': self.INTERNAL_AUTHENTICATION_TOKEN})
            except ConnectionError as err:
                message = 'Unable to establish connection to backend server'
                self.ravenSingleton.Client.captureMessage(err)
                raise osv.except_osv(('Error!'), (message))
            except Exception as err:
                message = 'Something went wrong'
                self.ravenSingleton.Client.captureMessage(err)
                raise osv.except_osv(('Error!'), (message))

    def validateHomeData(self, data):
        v = Validator()
        schema = {
            'name': {'type': 'string', 'empty': False},
            'street': {'type': 'string', 'empty': False},
            'zip': {'type': 'string', 'empty': False},
            'city':  {'type': 'string', 'empty': False},
            'odooID': {'type': 'number'},
            'subscriptionEndDate': {'type': 'string'},
            'status': {'type': 'string'},
        }
        result = v.validate(data, schema)
        if(not result):
            raise osv.except_osv(
                ('Error!'), ('Please assign an address to the contact'))
        return result
