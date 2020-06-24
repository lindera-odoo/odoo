from odoo import models, fields, api
from openerp.osv import osv
import requests as rq
import os
from . import backend_client
from datetime import datetime

homeMapping = {
    'einrichtung': 'home',
    'träger': 'company',
    'gruppe': 'organization'
}


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
        # Setup Lindera Backend Client Object
        backendClient = backend_client.BackendClient.setupBackendClient(self)

        parentId = self.parent_id.id
        tags = list(map(lambda tag: tag.name.lower(), self.category_id))
        name = self.name
        typeOfHome = list(
            filter(lambda tag: tag in homeMapping.keys(), tags))

        if len(typeOfHome) == 0:
            raise osv.except_osv(
                ('Error!'), ('All companies must have one of the following tags: "Einrichtung", "Träger" or "Gruppe"'))

        if len(typeOfHome) > 0:
            if len(typeOfHome) > 1:
                raise osv.except_osv(
                    ('Error!'), ('"Einrichtung", "Träger, "Gruppe" tags are not allowed to be used together'))
            if(len(typeOfHome) == 1):
                typeOfHome = typeOfHome[0]

            payload = {
                'name': self.name,
                'city': self.city,
                'street': self.street if self.street else '' + ' ' + self.street2 if self.street2 else '',
                'zip': self.zip,
                'role': homeMapping[typeOfHome],
                'odooID': self.id
            }

        if parentId:
            if self.type == 'contact':
                raise osv.except_osv(
                    ('Error!'), ('Address is missing'))
            # Check if parent contact exists in lindera DB
            parent = backendClient.getHome(parentId).json()

            # Parent contact does not exist in lindera DB
            if parent and parent['total'] == 0:
                parentData = self.env['res.partner'].search(
                    [('id', '=', parentId)])

                parentCompanyName = parentData.name

                parentTags = list(
                    map(lambda tag: tag.name.lower(), parentData.category_id))
                parentHomeType = list(
                    filter(lambda tag: tag in homeMapping.keys(), parentTags))

                if len(parentHomeType) > 1:
                    raise osv.except_osv(
                        ('Error!'), ('"Einrichtung", "Träger, "Gruppe" tags are not allowed to be used together'))
                if(len(parentHomeType) == 1):
                    parentHomeType = parentHomeType[0]
                if(len(parentHomeType) == 0):
                    raise osv.except_osv(
                        ('Error!'), ('Company {} does not have one of these tags: "Einrichtung", "Träger, "Gruppe"'.format(parentCompanyName)))

                if (typeOfHome == 'einrichtung' and (parentHomeType != 'träger')) or (typeOfHome == 'träger' and (parentHomeType != 'gruppe')):
                    raise osv.except_osv(
                        ('Error!'), ('{} and {} hierarchical relationship is not valid'.format(parentCompanyName, name)))

                # Then create it in lindera DB
                result = parentData.createHomeInLinderaDB()
                createdDocumentId = result['data']['_id']

                # Then create its child
                home = backendClient.postHome(payload).json()
                children = [home['data']['_id']]

            # Parent contact exists
            else:
                role = parent['data'][0]['role']
                parentCompanyName = parent['data'][0]['name']
                if (typeOfHome == 'gruppe' and (role == 'home' or role == 'company' or role == 'organization')) or (typeOfHome == 'einrichtung' and (role == 'home' or role == 'organization')) or (typeOfHome == 'träger' and (role == 'home' or role == 'company')):
                    raise osv.except_osv(
                        ('Error!'), ('{} can not be assigned as parent of {}'.format(parentCompanyName, name)))
                home = backendClient.postHome(payload).json()
                children = parent['data'][0]['children']
                children = list(
                    map(lambda child: child['_id'], children))

                newHomeId = home['data']['_id']
                children.append(newHomeId)
                createdDocumentId = parent['data'][0]['_id']

            updatedField = {
                'children': children
            }
            backendClient.updateHome(createdDocumentId, updatedField).json()
            return home
        else:
            return backendClient.postHome(payload).json()

    @api.multi
    def write(self, vals):
        if "category_id" in vals:
            previousContactTags = list(
                map(lambda tag: tag.name.lower(), self.category_id))
            newTags = vals['category_id'][0][2]
            newTags = list(
                map(lambda tagId: self.env['res.partner.category'].search([('id', '=', tagId)]).name.lower(), newTags))

            targetTags = list(
                filter(lambda tag: tag in homeMapping.keys(), newTags))

            if len(targetTags) > 1:
                raise osv.except_osv(
                    ('Error!'), ('"Einrichtung", "Träger, "Gruppe" tags are not allowed to be used together'))

            if len(targetTags) == 1:
                targetTag = targetTags[0]

                previousTargetTags = list(
                    filter(lambda tag: tag in homeMapping.keys(), previousContactTags))
                previousTargetTag = previousTargetTags[0]
                if previousTargetTag != targetTag:
                    raise osv.except_osv(
                        ('Error!'), ('You can not change the tag {} to {}'.format(previousTargetTag, targetTag)))

        result = super(Contact, self).write(vals)
        return result

    @api.model
    def create(self, val):
        res = super(Contact, self).create(val)
        isCompany = res.is_company
        companyType = res.company_type

        if isCompany and companyType == 'company':
            res.createHomeInLinderaDB()

        return res
