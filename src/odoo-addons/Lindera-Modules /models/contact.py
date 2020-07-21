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

    def inviteUser(self):
        contactEmail = self.email

        if not contactEmail:
            raise osv.except_osv(
                ('Error!'), ('We tried to invite {} to {} as an admin, but email did not find'.format(self.name, self.parent_id.name)))

        homeData = self.isHomeExistsInLinderaDB(self.parent_id.id)
        if homeData:
            mongodbId = homeData['data'][0]['_id']
        else:
            result = self.parent_id.createHomeInLinderaDB()
            mongodbId = result['data']['_id']

        data = {
            'email': [{"email": contactEmail}],
            'homeID': mongodbId,
            'role': 'home_admin'
        }
        bClient = backend_client.BackendClient.setupBackendClient(self)
        return bClient.inviteUser(data).json()

    @api.model
    def create(self, val):
        res = super(Contact, self).create(val)

        isCompany = res.is_company

        if isCompany:
            res.createHomeInLinderaDB()
            return res
        else:
            parentCompany = res.parent_id
            parentCompanyId = parentCompany.id
            if parentCompanyId:
                x = res.inviteUser()
                raise osv.except_osv(('Error!'), (x))
        return res

    @api.multi
    def write(self, vals):
        result = super(Contact, self).write(vals)
        contactId = self.id
        data = self.isHomeExistsInLinderaDB(contactId)

        if not data:
            return result

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

        result = super(Contact, self).write(vals)
        return result
