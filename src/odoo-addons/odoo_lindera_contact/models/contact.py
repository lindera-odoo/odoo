from odoo import models, fields, api
from openerp.osv import osv
import os
from raven import Client
from . import backend_client
from datetime import datetime


class Contact(models.Model):
    _inherit = 'res.partner'

    @api.model
    def create(self, val):
        res = super(Contact, self).create(val)

        isCompany = res.is_company
        companyType = res.company_type
        tags = list(map(lambda tag: tag.name, res.category_id))
        parentId = res.parent_id.id
        addressType = res.type

        def preparePayload(typeOfHome, data):
            if typeOfHome == 'Einrichtung':
                role = 'home'
            if typeOfHome == 'Träger':
                role = 'company'
            if typeOfHome == 'Gruppe':
                role = 'organization'

            payload = {
                'name': data.name,
                'city': data.city,
                'street': data.street,
                'zip': data.zip,
                'role': role,
                'odooID': data.id
            }
            return payload

        if isCompany and companyType == 'company':
            typeOfHome = list(
                filter(lambda tag: tag in ['Einrichtung', 'Gruppe', 'Träger'], tags))

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
                backend_client.postHome(payload)
                return res

            else:
                if addressType and addressType == 'contact':
                    raise osv.except_osv(('Error!'), ('Address is missing'))

                parent = backend_client.getHome(parentId).json()
                # If the resource (home/company/contact) is not in lindera backend, then create it
                if parent and parent['total'] == 0:
                    home = backend_client.postHome(payload).json()
                    parentData = self.env['res.partner'].search(
                        [('id', '=', parentId)])
                    if parentData:
                        if(typeOfHome == 'Einrichtung'):
                            payload = preparePayload('Träger', parentData)
                        elif(typeOfHome == 'Träger'):
                            payload = preparePayload('Gruppe', parentData)

                        parentId = backend_client.postHome(
                            payload).json()['data']['_id']

                        children = [home['data']['_id']]

                # If the resource (home/company/contact) exists in lindera backend, then update the children field with the newly created resource ID
                elif parent and parent['total'] >= 1:
                    role = parent['data'][0]['role']
                    if (typeOfHome == 'Einrichtung' and (role == 'home' or role == 'organization')) or (typeOfHome == 'Träger' and (role == 'home' or role == 'company')):
                        raise osv.except_osv(
                            ('Error!'), ('This contact can not be assigned as parent'))

                    home = backend_client.postHome(payload).json()
                    children = parent['data'][0]['children']
                    children = list(map(lambda child: child['_id'], children))

                    newHomeId = home['data']['_id']
                    children.append(newHomeId)

                    parentId = parent['data'][0]['_id']

                updatedField = {
                    'children': children
                }
                backend_client.updateHome(parentId, updatedField)

        return res
