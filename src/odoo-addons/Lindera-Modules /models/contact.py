from odoo import models, fields, api
from openerp.osv import osv
import requests as rq
import os
from . import backend_client
from datetime import datetime


class Contact(models.Model):
    _inherit = 'res.partner'
    
    homeID = fields.Text('homeID', store=False, compute='_add_empty_homeID')

    def _add_empty_homeID(self):
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
        for contact in self:
            tags = list(map(lambda tag: tag.name.lower(), contact.category_id))
            contact.homeID = ''
            if 'einrichtung' in tags:
                home = backendClient.getHome(contact.id).json()
                if home and home['total'] != 0:
                    contact.homeID = home['data'][0]['_id']
    
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
                'odooID': self.id,
                'status': 'registered',
            }
            return backendClient.postHome(payload).json()

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

        if data:
            updatedData = {}

            if "name" in vals:
                updatedData['name'] = vals['name']

            if "street" in vals:
                updatedData['street'] = vals['street']

            if "street2" in vals:
                updatedData['street'] = updatedData['street'] + vals['street2']

            if "city" in vals:
                updatedData['city'] = vals['city']

            if "zip" in vals:
                updatedData['zip'] = vals['zip']

            homeMongodbId = data['data'][0]['_id']
            self.updateHome(homeMongodbId, updatedData)

        return super(Contact, self).write(vals)
