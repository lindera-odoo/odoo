from odoo import models, fields, api
from openerp.osv import osv
import requests as rq
import os
from . import backend_client
from datetime import datetime


class Contact(models.Model):
    _inherit = 'res.partner'

    def createHomeInLinderaDB(self):
        isCompany = self.is_company
        companyType = self.company_type

        if isCompany and companyType == 'company':
            # Setup Lindera Backend Client Object
            backendClient = backend_client.BackendClient.setupBackendClient(
                self)
            payload = {
                'name': self.name,
                'street': self.street if self.street else '' + ',' + self.street2 if self.street2 else '',
                'city': self.city,
                'zip': self.zip,
                'odooID': self.id
            }
            backendClient.postHome(payload).json()

    def isHomeExistsInLinderaDB(self, homeId):
        bClient = backend_client.BackendClient.setupBackendClient(self)
        homeData = bClient.getHome(homeId).json()
        if homeData['total'] == 0 and len(homeData['data']) == 0:
            return False
        else:
            return homeData

    def updateHome(self, mongodbId, data):
        bClient = backend_client.BackendClient.setupBackendClient(self)
        return bClient.updateHome(mongodbId, data)

    @api.model
    def create(self, val):
        res = super(Contact, self).create(val)
        res.createHomeInLinderaDB()
        return res

    @api.multi
    def write(self, vals):
        contactId = self.id
        data = self.isHomeExistsInLinderaDB(contactId)

        if not data:
            return

        updatedData = {}

        if "name" in vals:
            updatedData['name'] = vals['name']

        if "street" in vals:
            updatedData['street'] = vals['street']

        if "street2" in vals:
            updatedData['street'] = updatedData['street'] +
            ' ' + vals['street2']

        if "city" in vals:
            updatedData['city'] = vals['city']

        if "zip" in vals:
            updatedData['zip'] = vals['zip']

        homeMongodbId = data['data'][0]['_id']
        self.updateHome(homeMongodbId, updatedData)

        result = super(Contact, self).write(vals)
        return result

    # @api.model
    # def create(self, val):
    #     res = super(Contact, self).create(val)

    #     isCompany = res.is_company
    #     companyType = res.company_type
    #     tags = list(map(lambda tag: tag.name.lower(), res.category_id))
    #     parentId = res.parent_id.id
    #     addressType = res.type

    #     url = self.env['ir.config_parameter'].get_param('lindera.backend')
    #     token = self.env['ir.config_parameter'].get_param(
    #         'lindera.internal_authentication_token')
    #     ravenClient = self.env['ir.config_parameter'].get_param(
    #         'lindera.raven_client')

    #     if (url and token and ravenClient):
    #         backendClient = backend_client.BackendClient(
    #             url, token, ravenClient)
    #     else:
    #         raise osv.except_osv(
    #             ('Error!'), ('Please, setup system parameters for lindera backend'))

    #     def preparePayload(typeOfHome, data):
    #         payload = {
    #             'name': data.name,
    #             'city': data.city,
    #             'street': data.street,
    #             'zip': data.zip,
    #             'role': homeMapping[typeOfHome],
    #             'odooID': data.id
    #         }

    #         return payload

    #     if isCompany and companyType == 'company':
    #         typeOfHome = list(
    #             filter(lambda tag: tag in homeMapping.keys(), tags))

    #         if len(typeOfHome) == 0:
    #             raise osv.except_osv(
    #                 ('Error!'), ('All companies must have one of the following tags: "Einrichtung", "Träger" or "Gruppe"'))

    #         if len(typeOfHome) > 0:
    #             if len(typeOfHome) > 1:
    #                 raise osv.except_osv(
    #                     ('Error!'), ('"Einrichtung", "Träger, "Gruppe" tags are not allowed to be used together'))
    #             if(len(typeOfHome) == 1):
    #                 typeOfHome = typeOfHome[0]

    #             payload = preparePayload(typeOfHome, res)

    #             if not parentId:
    #                 backendClient.postHome(payload)
    #                 return res

    #             else:
    #                 if addressType and addressType == 'contact':
    #                     raise osv.except_osv(
    #                         ('Error!'), ('Address is missing'))

    #                 parent = backendClient.getHome(parentId).json()
    #                 # If the resource (home/company/contact) is not in lindera backend, then create it
    #                 if parent and parent['total'] == 0:
    #                     home = backendClient.postHome(payload).json()
    #                     parentData = self.env['res.partner'].search(
    #                         [('id', '=', parentId)])
    #                     if parentData:
    #                         if(typeOfHome == 'einrichtung'):
    #                             payload = preparePayload('träger', parentData)
    #                         elif(typeOfHome == 'träger'):
    #                             payload = preparePayload('gruppe', parentData)

    #                         parentId = backendClient.postHome(
    #                             payload).json()['data']['_id']

    #                         children = [home['data']['_id']]

    #                 # If the resource (home/company/contact) exists in lindera backend, then update the children field with the newly created resource ID
    #                 elif parent and parent['total'] >= 1:
    #                     role = parent['data'][0]['role']
    #                     if (typeOfHome == 'einrichtung' and (role == 'home' or role == 'organization')) or (typeOfHome == 'träger' and (role == 'home' or role == 'company')):
    #                         raise osv.except_osv(
    #                             ('Error!'), ('This contact can not be assigned as parent'))

    #                     home = backendClient.postHome(payload).json()
    #                     children = parent['data'][0]['children']
    #                     children = list(
    #                         map(lambda child: child['_id'], children))

    #                     newHomeId = home['data']['_id']
    #                     children.append(newHomeId)

    #                     parentId = parent['data'][0]['_id']

    #                 updatedField = {
    #                     'children': children
    #                 }
    #                 backendClient.updateHome(parentId, updatedField)

    #     return res
