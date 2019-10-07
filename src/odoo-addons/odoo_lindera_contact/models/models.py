from odoo import models, fields, api
from openerp.osv import osv
import pprint
import inspect
import requests as rq
import os
from cerberus import Validator

INTERNAL_AUTHENTICATION_TOKEN = os.getenv("LINDERA_INTERNAL_AUTHENTICATION_TOKEN")
URL = os.getenv("LINDERA_API_URL")

print("outside LinderaBackend class")


class LinderaBackend(models.Model):
    _inherit = 'res.partner'

    print("inside models.py")

    @api.model
    def create(self, val):
        res = super(LinderaBackend, self).create(val)


        def callLinderaAPI(data):
            rq.post("{}/homes".format(URL), json=data, headers={'token': INTERNAL_AUTHENTICATION_TOKEN})

        def validateData(data):
            v = Validator()
            schema = {
                'name': {'type': 'string'}, # map
                'role': {'type': 'string', 'allowed': ['home', 'company', 'organization']},
                'street': {'type': 'string'},
                'zip': {'type': 'string'},
                'city':  {'type': 'string'},
                # 'countrycodeISO316a2':  {'type': 'string'},  # map
            }
            result = v.validate(data, schema)
            return result


        tag = res.category_id
        if tag:
            tags = []
            for item in tag:
                tags.append(item.name)

            # Check if 'Träger' is in the list
            if 'Träger' in tags:
                document = {
                    'name': res.name,
                    'city': res.city,
                    'street': res.street,
                    'zip': res.zip,
                    'role': 'company'
                }

                if (validateData(document)):
                    callLinderaAPI(document)
                else:
                    raise osv.except_osv(('Error!'), ('Invalid input data, address is missing'))

             # Check if 'Einrichtung' is in the list
            if 'Einrichtung' in tags:
                document = {
                    'name': res.name,
                    'city': res.city,
                    'street': res.street,
                    'zip': res.zip,
                    'role': 'home'
                }
                if (validateData(document)):
                    callLinderaAPI(document)
                else:
                    raise osv.except_osv(('Error!'), ('Invalid input data, address is missing'))
                
            
        else:
            print("something")
   
    
        return res



class linderaApi(models.Model):
    _name = "lindera.api"
    _description = "lindera api related info"
