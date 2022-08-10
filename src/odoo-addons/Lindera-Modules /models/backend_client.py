from odoo import models, fields, api
import requests as rq
import os
from cerberus import Validator
from .ravenSingleton import ravenSingleton
from dotenv import load_dotenv
from openerp.osv import osv
from requests.exceptions import ConnectionError
import json

MAX_ATTEMPTS = 30
SLEEP_BETWEEN_ATTEMPS = 1

class BackendClient():
    instance = None
    def __init__(self, url, ravenClient, user, pw):
        self.URL = url
        self.INTERNAL_AUTHENTICATION_TOKEN = ''
        self.ravenSingleton = ravenSingleton(ravenClient)
        self.user = user
        self.pw = pw

    def _connect(self):
        attempt = 0
        lastException = None
        while attempt < MAX_ATTEMPTS:
            attempt += 1
            try:
                if self.INTERNAL_AUTHENTICATION_TOKEN == '':
                    headers = {'content-type': 'application/json',
                               'accept': 'application/json'}
                    resp = rq.post(url=self.URL + '/session',
                                         json={'email': self.user, 'password': self.pw},
                                         headers=headers)
                    data1 = json.loads(resp.text)
                    assert resp.status_code == 200, 'not logged in'

                    self.INTERNAL_AUTHENTICATION_TOKEN = data1['token']
                    return self.INTERNAL_AUTHENTICATION_TOKEN
                else:
                    # this is just a connection test
                    resp = rq.get(url=self.URL + '/users',
                                  headers={'token': self.INTERNAL_AUTHENTICATION_TOKEN})
                    data1 = json.loads(resp.text)['data']
                    return self.INTERNAL_AUTHENTICATION_TOKEN
            except Exception as e:
                lastException = e
                print(e)
                import time
                time.sleep(SLEEP_BETWEEN_ATTEMPS)
                self.INTERNAL_AUTHENTICATION_TOKEN = ''
    
        error_str = "Maximum number of attempts reached: {}. Aborting connection.".format(
            MAX_ATTEMPTS)
        print(error_str)
        raise lastException

    @classmethod
    def setupBackendClient(cls, context):
        if cls.instance is None:
            url = context.env['ir.config_parameter'].get_param('lindera.backend')
    
            ravenClient = context.env['ir.config_parameter'].get_param(
                'lindera.raven_client')
            user = context.env['ir.config_parameter'].get_param(
                'lindera.internal_user_email')
            pw = context.env['ir.config_parameter'].get_param(
                'lindera.internal_user_pw')
    
            if (url and ravenClient and user and pw):
                client = cls(url, ravenClient, user, pw)
                cls.instance = client
                return client
            else:
                raise osv.except_osv(
                    ('Error!'), ('Please, setup system parameters for lindera backend'))
        else:
            return cls.instance

    def notifyBackendToCreateReport(self, data):
        try:
            self._connect()
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
                self._connect()
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
            self._connect()
            return rq.get(self.URL+"/homes?filter={}={}".format('odooID', id), headers={'token': self.INTERNAL_AUTHENTICATION_TOKEN})
        except ConnectionError as err:
            message = 'Unable to establish connection to backend server'
            self.ravenSingleton.Client.captureMessage(err)
            raise osv.except_osv(('Error!'), (message))
        except Exception as err:
            message = 'Something went wrong'
            self.ravenSingleton.Client.captureMessage(err)
            raise osv.except_osv(('Error!'), (message))
    
    def getHomeById(self, id):
        try:
            self._connect()
            return rq.get(self.URL+"/homes/{}".format(id), headers={'token': self.INTERNAL_AUTHENTICATION_TOKEN})
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
                self._connect()
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
            'odooID': {'type': 'number', 'nullable': True},
            'subscriptionEndDate': {'type': 'string'},
            'status': {'type': 'string'},
        }
        result = v.validate(data, schema)
        if(not result):
            raise osv.except_osv(
                ('Error!'), ('Please assign an address to the contact' + str(result)))
        return result
    
    def getUser(self, email):
        try:
            self._connect()
            return rq.get(self.URL+"/users?filter={}={}".format('email', email), headers={'token': self.INTERNAL_AUTHENTICATION_TOKEN})
        except ConnectionError as err:
            message = 'Unable to establish connection to backend server'
            self.ravenSingleton.Client.captureMessage(err)
            raise osv.except_osv(('Error!'), (message))
        except Exception as err:
            message = 'Something went wrong'
            self.ravenSingleton.Client.captureMessage(err)
            raise osv.except_osv(('Error!'), (message))
    
    def validateUserData(self, data):
        v = Validator()
        schema = {
            'homeID': {'type': 'string', 'empty': False},
            'email': {'type': 'string', 'empty': False},
            'firstname': {'type': 'string'},
            'lastname': {'type': 'string'},
            'language': {'type': 'string', 'empty': False},
        }
        result = v.validate(data, schema)
        if (not result):
            raise osv.except_osv(
                ('Error!'), ('Please assign an email to the contact'))
        return result
    
    def postUser(self, data):
        if self.validateUserData(data):
            try:
                self._connect()
                data = {
                    'homeID': data['homeID'],
                    'email': [data],
                    'firstname': data['firstname'],
                    'lastname': data['lastname'],
                    'language': data['language'],
                }
                return rq.post("{}/users/invite".format(self.URL), json=data, headers={'token': self.INTERNAL_AUTHENTICATION_TOKEN})
            except ConnectionError as err:
                message = 'Unable to establish connection to backend server'
                self.ravenSingleton.Client.captureMessage(err)
                raise osv.except_osv(('Error!'), (message))
            except Exception as err:
                self.ravenSingleton.Client.captureMessage(err)
                raise osv.except_osv(('Error!'), (self.URL, err))