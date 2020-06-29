from odoo import models, fields, api
from openerp.osv import osv
import requests as rq
import os
from . import backend_client
from datetime import datetime


class Contact(models.Model):
    _inherit = 'res.partner'

    def updateHome(self, mongodbId, data):
        bClient = backend_client.BackendClient.setupBackendClient(self)
        return bClient.updateHome(mongodbId, data)

    def isHomeExistsInLinderaDB(self, homeId):
        bClient = backend_client.BackendClient.setupBackendClient(self)
        homeData = bClient.getHome(homeId).json()
        if homeData['total'] == 0 and len(homeData['data']) == 0:
            return False
        else:
            return homeData

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

            print("test")
            return payload
  
            backendClient.postHome(payload).json()
            print("tset")

    @api.multi
    def write(self, vals):
        contactId = self.id

        data = self.isHomeExistsInLinderaDB(contactId)

        subscription = self.env['sale.subscription'].search(
            [('partner_id', '=', contactId)])

        raise osv.except_osv(
            ('Error!'), (type(subscription)))

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

    @api.model
    def create(self, val):
        res = super(Contact, self).create(val)
        res.createHomeInLinderaDB()
        return res
