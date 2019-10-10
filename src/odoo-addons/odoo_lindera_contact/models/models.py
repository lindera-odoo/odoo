import logging
from odoo import models, fields, api
from openerp.osv import osv
import pprint
import inspect
import requests as rq
import os
from cerberus import Validator

_logger = logging.getLogger(__name__)

URL = 'https://backend-testing.lindera.de/v2/homes'
INTERNAL_AUTHENTICATION_TOKEN = 'Bearer HfpWLjqt5k0YqIjPgYtb'

class LinderaBackend(models.Model):
    _inherit = 'res.partner'

    @api.model
    def create(self, val):
        res = super(LinderaBackend, self).create(val)

        # LINDERA API (homes resource)
        def postHome(data):
            return rq.post("{}/homes".format(URL), json=data, headers={'token': INTERNAL_AUTHENTICATION_TOKEN})
        
        def getHome(id):
            return rq.get(URL+"/homes/?filter={}={}".format('odooID', id), headers={'token': INTERNAL_AUTHENTICATION_TOKEN})

        def updateHome(id, data):
            return rq.put("{}/homes/{}".format(URL, id), json=data, headers={'token': INTERNAL_AUTHENTICATION_TOKEN})

        
        # validator
        def validateData(data):
            v = Validator()
            schema = {
                'name': {'type': 'string'}, # map
                'role': {'type': 'string', 'allowed': ['home', 'company', 'organization']},
                'street': {'type': 'string'},
                'zip': {'type': 'string'},
                'city':  {'type': 'string'},
                'odooID': {'type': 'number'},
                'children': {'type': 'list'}
            }
            result = v.validate(data, schema)
            return result
        

        def linderaAPI(data):
            if (validateData(data)):
                result = postHome(data)
                return result
            else:
                raise osv.except_osv(('Error!'), ('Invalid input data, address is missing'))



        
        isCompany = res.is_company
        companyType = res.company_type
        tag = res.category_id
        parentId = res.parent_id.id

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
                # prepare data to send for lindera API
                data = {
                    'name': res.name,
                    'city': res.city,
                    'street': res.street,
                    'zip': res.zip,
                    'role': 'home',
                    'odooID': res.id
                }

                if parentId:
                    if res.type == 'contact':
                        raise osv.except_osv(('Error!'), ('Address is missing'))

                    response = getHome(parentId).json()
                    
                    # If the resource (home/company/contact) is not in lindera backend, then create it
                    if response and response['total'] == 0:
                        result = self.env['res.partner'].search([('id','=',parentId)])
                        doc = {
                            'name': result.name,
                            'city': result.city,
                            'street': result.street,
                            'zip': result.zip,
                            'role': 'company',
                            'odooID': result.id,
                        }

                        rid = postHome(doc).json()['data']['_id']

                        returnedValue = linderaAPI(data).json()
                        _id = returnedValue['data']['_id']


                        updatedField = {
                            'children': [
                                _id
                            ]
                        }
                        # update children with ID
                        updateHome(rid, updatedField) 
                    
                    # If the resource exists, then update the children field with the newly created resource ID 
                    if response and response['total'] == 1:
                        
                        resourceid = response['data'][0]['_id']
                        currentValues = []
                        for id in response['data'][0]['children']:
                            currentValues.append(id['_id'])
                            
                        v = linderaAPI(data).json()
                        oid = v['data']['_id']

                        currentValues.append(oid)
                        
                        updatedField = {
                            'children': currentValues
                        }
                        # update children with ID
                        updateHome(resourceid, updatedField)
                    
                linderaAPI(data)

            # if 'Träger' in tags:
            #     # prepare data to send for lindera API
            #     data = {
            #         'name': res.name,
            #         'city': res.city,
            #         'street': res.street,
            #         'zip': res.zip,
            #         'role': 'company',
            #         'odooID': res.id
            #     }
        return res
  



class linderaApi(models.Model):
    _name = "lindera.api"
    _description = "lindera api related info"
