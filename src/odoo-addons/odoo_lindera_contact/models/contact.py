from odoo import models, fields, api
from openerp.osv import osv
import requests as rq
import os
from . import backend_client
from datetime import datetime


class Contact(models.Model):
    _inherit = 'res.partner'

    @api.model
    def create(self, val):
        res = super(Contact, self).create(val)

        isCompany = res.is_company
        companyType = res.company_type
        tags = list(map(lambda tag: tag.name.lower(), res.category_id))
        parentId = res.parent_id.id
        addressType = res.type

        url = self.env['ir.config_parameter'].get_param('lindera.backend')
        token = self.env['ir.config_parameter'].get_param(
            'lindera.internal_authentication_token')
        ravenClient = self.env['ir.config_parameter'].get_param(
            'lindera.raven_client')

        if (url and token and ravenClient):
            backendClient = backend_client.BackendClient(
                url, token, ravenClient)
        else:
            raise osv.except_osv(
                ('Error!'), ('Please, setup system parameters for lindera backend'))

        def preparePayload(typeOfHome, data):
            homeMapping = {
                'einrichtung': 'home',
                'träger': 'company',
                'gruppe': 'organization',
                'salespartner': 'home',
                'versicherung': 'home'
            }

            payload = {
                'name': data.name,
                'city': data.city,
                'street': data.street,
                'zip': data.zip,
                'role': homeMapping[typeOfHome],
                'odooID': data.id
            }

            return payload

        if isCompany and companyType == 'company':
            typeOfHome = list(
                filter(lambda tag: tag in ['einrichtung', 'gruppe', 'träger', 'salespartner', 'versicherung'], tags))

            if len(typeOfHome) > 1:
                raise osv.except_osv(
                    ('Error!'), ('These tags are not allowed to be used together'))
            if len(tags) == 0:
                raise osv.except_osv(('Error!'), ('Please select a tag'))
            elif(len(typeOfHome) == 1):
                typeOfHome = typeOfHome[0]
            else:
                return res

            payload = preparePayload(typeOfHome, res)

            if not parentId:
                backendClient.postHome(payload)
                return res

            else:
                if addressType and addressType == 'contact':
                    raise osv.except_osv(('Error!'), ('Address is missing'))

                parent = backendClient.getHome(parentId).json()
                # If the resource (home/company/contact) is not in lindera backend, then create it
                if parent and parent['total'] == 0:
                    home = backendClient.postHome(payload).json()
                    parentData = self.env['res.partner'].search(
                        [('id', '=', parentId)])
                    if parentData:
                        if(typeOfHome == 'einrichtung'):
                            payload = preparePayload('träger', parentData)
                        elif(typeOfHome == 'träger'):
                            payload = preparePayload('gruppe', parentData)

                        parentId = backendClient.postHome(
                            payload).json()['data']['_id']

                        children = [home['data']['_id']]

                # If the resource (home/company/contact) exists in lindera backend, then update the children field with the newly created resource ID
                elif parent and parent['total'] >= 1:
                    role = parent['data'][0]['role']
                    if (typeOfHome == 'einrichtung' and (role == 'home' or role == 'organization')) or (typeOfHome == 'träger' and (role == 'home' or role == 'company')):
                        raise osv.except_osv(
                            ('Error!'), ('This contact can not be assigned as parent'))

                    home = backendClient.postHome(payload).json()
                    children = parent['data'][0]['children']
                    children = list(map(lambda child: child['_id'], children))

                    newHomeId = home['data']['_id']
                    children.append(newHomeId)

                    parentId = parent['data'][0]['_id']

                updatedField = {
                    'children': children
                }
                backendClient.updateHome(parentId, updatedField)

        return res
