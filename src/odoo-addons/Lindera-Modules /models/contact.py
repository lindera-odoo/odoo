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

    @api.model
    def create(self, val):
        if not val['is_company']:
            special_tags = 0
            for id in val['category_id'][0][2]:
                cat = self.env['res.partner.category'].browse(id)
                if 'einrichtung' in cat.name.lower():
                    special_tags += 1
                if 'träger' in cat.name.lower():
                    special_tags += 1
                if 'gruppe' in cat.name.lower():
                    special_tags += 1
            if special_tags > 0:
                raise osv.except_osv(
                    ('Error!'),
                    ('Only companies are allowed to use the tags: "Einrichtung", "Träger" or "Gruppe"'))
        res = super(Contact, self).create(val)
        res.createHomeInLinderaDB()
        return res

    @api.multi
    def write(self, vals):
        for contact in self:
            if 'category_id' in vals.keys() or 'is_company' in vals.keys():
                tags = list(map(lambda tag: tag.name.lower(), contact.category_id))
                is_company = contact.is_company
                if 'category_id' in vals.keys():
                    tags = []
                    for id in vals['category_id'][0][2]:
                        cat = self.env['res.partner.category'].browse(id)
                        tags.append(cat.name.lower())
                if 'is_company' in vals.keys():
                    is_company = vals['is_company']
                
                if not is_company:
                    special_tags = 0
                    if 'einrichtung' in tags:
                        special_tags += 1
                    if 'träger' in tags:
                        special_tags += 1
                    if 'gruppe' in tags:
                        special_tags += 1
    
                    if special_tags > 0:
                        raise osv.except_osv(
                            ('Error!'),
                            ('Only companies are allowed to use the tags: "Einrichtung", "Träger" or "Gruppe"'))
            
            contactId = contact.id
            data = contact.isHomeExistsInLinderaDB(contactId)
    
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
                contact.updateHome(homeMongodbId, updatedData)

        return super(Contact, self).write(vals)
