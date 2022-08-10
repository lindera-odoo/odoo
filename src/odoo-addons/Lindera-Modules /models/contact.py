from odoo import models, fields, api
from openerp.osv import osv
import requests as rq
import os
from . import backend_client
from datetime import datetime
from odoo.tools import pycompat

Languages = {
    'de_DE': 'deu',
    'fr_FR': 'fra',
    'pt_BR': 'por',
    'en_US': 'eng',
    'en_GB': 'eng'
}

class Contact(models.Model):
    _inherit = 'res.partner'
    
    homeID = fields.Text('homeID', store=False, compute='_add_empty_homeID')

    def _add_empty_homeID(self):
        for contact in self:
            contact.homeID = ''
            if contact.is_company:
                backend_id = self.env['lindera.backend.id'].search([("contact_id", "=", contact.id)])
                if backend_id:
                    contact.homeID = backend_id[0].home_id
                else:
                    backendClient = backend_client.BackendClient.setupBackendClient(self)
                    home = backendClient.getHome(contact.id).json()
                    if home and home['total'] != 0:
                        if len(home['data']) > 1:
                            # take the one that was created the latest.
                            data = home['data'][-1]
                            # clear the odooID of the others, since their odoo contact was deleted at some point
                            for to_clear in home['data']:
                                if to_clear['_id'] != data['_id']:
                                    backendClient.updateHome(to_clear['_id'], {'odooID': None})

                        else:
                            data = home['data'][0]
                        contact.homeID = data['_id']
                        
                        self.env['lindera.backend.id'].create({
                            'contact_id': contact.id,
                            'home_id': contact.homeID
                        })
    
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
            response = backendClient.postHome(payload).json()
            self.env['lindera.backend.id'].create({
                'contact_id': self.id,
                'home_id': response['data']['_id']
            })
            return response

    def isHomeExistsInLinderaDB(self, homeId):
        bClient = backend_client.BackendClient.setupBackendClient(self)
        homeData = bClient.getHome(homeId).json()
        if homeData['total'] == 0 and len(homeData['data']) == 0:
            return False
        else:
            return homeData
        
    def createUser(self, homeID):
        if self.email:
            bClient = backend_client.BackendClient.setupBackendClient(self)
            userData = bClient.getUser(self.email).json()
            if userData['total'] == 0 and len(userData['data']) == 0:
                firstname = 'firstname'
                lastname = 'lastname'
                name_parts = self.name.split(' ')
                if len(name_parts) > 0:
                    firstname = name_parts[0]
                if len(name_parts) > 1:
                    lastname = name_parts[1]
                bClient.postUser({
                    'homeID': homeID,
                    'email': self.email,
                    'firstname': firstname,
                    'lastname': lastname,
                    'language': Languages[self.lang]
                })

    def updateHome(self, mongodbId, data):
        bClient = backend_client.BackendClient.setupBackendClient(self)
        return bClient.updateHome(mongodbId, data)
        
    @api.model
    def create(self, val):
        if 'is_company' in val.keys() and not val['is_company'] and 'category_id' in val.keys():
            special_tags = 0
            if len(val['category_id']) > 0 and len(val['category_id'][0]) >= 3:
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
            
            tags = list(map(lambda tag: tag.name.lower(), contact.category_id))
            if 'category_id' in vals.keys():
                tags = []
                for id in vals['category_id'][0][2]:
                    cat = self.env['res.partner.category'].browse(id)
                    tags.append(cat.name.lower())

            is_company = contact.is_company
            if 'is_company' in vals.keys():
                is_company = vals['is_company']
                
            contactId = contact.id
            data = contact.isHomeExistsInLinderaDB(contactId)
            
            if not data:
                backend_ids = self.env['lindera.backend.id'].search([("contact_id", "=", contact.id)])
                if backend_ids:
                    backendClient = backend_client.BackendClient.setupBackendClient(self)
                    data = backendClient.getHomeById(backend_ids[0].home_id)
                    homeMongodbId = backend_ids[0].home_id
            else:
                homeMongodbId = data['data'][0]['_id']
    
            if data:
                updatedData = {"odooID": contactId}
    
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
    
                contact.updateHome(homeMongodbId, updatedData)
            elif ('einrichtung' in tags or 'träger' in tags or 'gruppe' in tags) and is_company and\
                    isinstance(contactId, pycompat.integer_types):
                contact.createHomeInLinderaDB()
                

        return super(Contact, self).write(vals)

    @api.multi
    def unlink(self):
        for contact in self:
            if contact.is_company:
                backend_ids = self.env['lindera.backend.id'].search([("contact_id", "=", contact.id)])
                
                # should only ever be one, but since odoo does not have 1 to 1 relations
                # it is in theory possible to have multiple here
                for backend_id in backend_ids:
                    # clear the odooID, so that odoo can use the ID again, without breaking the link to the backend
                    contact.updateHome(backend_id.home_id, {'odooID': None})
                    
        return super(Contact, self).unlink()