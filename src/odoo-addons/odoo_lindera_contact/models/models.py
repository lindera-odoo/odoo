from odoo import models, fields, api
from openerp.osv import osv
import pprint
import inspect
import requests as rq
import os
from cerberus import Validator
from raven import Client

URL = 'https://backend-testing.lindera.de/v2'
INTERNAL_AUTHENTICATION_TOKEN = 'Bearer HfpWLjqt5k0YqIjPgYtb'
client = Client('https://2f93ec8aba4c419a836337bd8ff4b427:53d79797dd0642218c08b664581e4e6d@sentry.lindera.de/6')


class LinderaBackend(models.Model):
    _inherit = 'res.partner'
    @api.model
    def create(self, val):
        res = super(LinderaBackend, self).create(val)

        isCompany = res.is_company
        companyType = res.company_type
        tag = res.category_id
        parentId = res.parent_id.id
        addressType = res.type

        # LINDERA API (homes resource)
        def postHome(data):
            try:
                return rq.post("{}/homes".format(URL), json=data, headers={'token': INTERNAL_AUTHENTICATION_TOKEN})
            except:
                client.captureMessage('Lindera backend failed to create the resource (home)')
        
        def getHome(id):
            try:
                return rq.get(URL+"/homes?filter={}={}".format('odooID', id), headers={'token': INTERNAL_AUTHENTICATION_TOKEN})
            except:
                client.captureMessage('Lindera backend failed to fetch the resource (home)')

        def updateHome(id, data):
            try:
                return rq.put("{}/homes/{}".format(URL, id), json=data, headers={'token': INTERNAL_AUTHENTICATION_TOKEN})
            except:
                client.captureMessage('Lindera backend failed to update the resource (home)')


        
        # validator
        def validateData(data):
            v = Validator()
            schema = {
                'name': {'type': 'string', 'empty': False }, # map
                'role': {'type': 'string', 'allowed': ['home', 'company', 'organization']},
                'street': {'type': 'string', 'empty': False},
                'zip': {'type': 'string', 'empty': False},
                'city':  {'type': 'string', 'empty': False},
                'odooID': {'type': 'number'},
                'children': {'type': 'list'}
            }
            result = v.validate(data, schema)
            return result

        
        def preparePayload(tag):
            data = {}
            if tag == 'Einrichtung':
                data = {
                    'name': res.name,
                    'city': res.city,
                    'street': res.street,
                    'zip': res.zip,
                    'role': 'home',
                    'odooID': res.id
                }
            if tag == 'Träger':
                data = {
                    'name': res.name,
                    'city': res.city,
                    'street': res.street,
                    'zip': res.zip,
                    'role': 'company',
                    'odooID': res.id
                }
            return data

        def createHome(payload):
            result = validateData(payload)
            if result:
                postHome(payload)
            else:
                raise osv.except_osv(('Error!'), ('Invalid input data, address is missing'))
        
        def process(tag, data):
            if addressType and addressType == 'contact':
                raise osv.except_osv(('Error!'), ('Address is missing'))
            
            response = getHome(parentId).json()

            # If the resource (home/company/contact) is not in lindera backend, then create it
            if response and response['total'] == 0:
                result = self.env['res.partner'].search([('id','=',parentId)])
                if result:
                    if tag == 'Einrichtung':
                        payload = {
                            'name': result.name,
                            'city': result.city,
                            'street': result.street,
                            'zip': result.zip,
                            'role': 'company',
                            'odooID': result.id
                        }
                    
                    if tag == 'Träger':
                        payload = {
                            'name': result.name,
                            'city': result.city,
                            'street': result.street,
                            'zip': result.zip,
                            'role': 'organization',
                            'odooID': result.id
                        }
                if validateData(payload):
                    documentId = postHome(payload).json()['data']['_id']
                else:
                    raise osv.except_osv(('Error!'), ('Parent company does not have proper address'))

                # Create the child resource (home/company/contact) and get the ID
                if validateData(data):
                    result = postHome(data).json()
                
                _id = result['data']['_id']
                updatedField = {
                    'children': [
                        _id
                    ]
                }
                # update the parent resource (children field) with new data
                updateHome(documentId, updatedField) 

            # If the resource (home/company/contact) exists in lindera backend, then update the children field with the newly created resource ID 
            if response and response['total'] == 1 :
                resourceid = response['data'][0]['_id']
                currentValues = []
                for child in response['data'][0]['children']:
                    currentValues.append(child['_id'])
                        
                if validateData(data):
                    result = postHome(data).json()

                newResourceId = result['data']['_id']
                currentValues.append(newResourceId)
                        
                updatedField = {
                    'children': currentValues
                }
                # update children with ID
                updateHome(resourceid, updatedField)
            


        if isCompany and companyType == 'company':
            if len(tag) == 0:
                raise osv.except_osv(('Error!'), ('Missing tag'))

            tags = []
            for item in tag:
                tags.append(item.name)
            

            # TODO: This part of the code should be optimized --
            first = ['Träger', 'Einrichtung', 'Gruppe']
            second = ['Träger', 'Einrichtung']
            third = ['Träger', 'Gruppe']
            forth = ['Einrichtung', 'Gruppe']

            if all(item in tags for item in first) or all(item in tags for item in second) or all(item in tags for item in third) or all(item in tags for item in forth):
                raise osv.except_osv(('Error!'), ('These tags are not allowed to be used together'))
            

            if 'Einrichtung' in tags:
                payload = preparePayload('Einrichtung')
                
                if parentId:
                    process('Einrichtung', payload)

                else:
                    createHome(payload)
            
            if 'Träger' in tags:
                payload = preparePayload('Träger')

                if parentId:
                    process('Träger', payload)
                     
                else:
                    createHome(payload)
            
        return res
  



class linderaApi(models.Model):
    _name = "lindera.api"
    _description = "lindera api related info"
