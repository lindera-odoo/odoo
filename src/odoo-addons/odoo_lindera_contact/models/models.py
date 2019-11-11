from odoo import models, fields, api
from openerp.osv import osv
import pprint
import inspect
import requests as rq
import os
from raven import Client
from . import backend_client
from datetime import datetime

def getCurrentTimestamp():
    return datetime.now().timestamp().__round__()

class LinderaCRM(models.Model):
    _inherit = 'crm.lead'

    @api.multi 
    def write(self, vals):
        result = super(LinderaCRM, self).write(vals)

        if 'stage_id' not in vals:
            return
        
        id = vals['stage_id']
        findStageById = self.env['crm.stage'].search([('id', '=', id)])
        name = findStageById.name
        # Get the current timestamp in seconds
        cts = getCurrentTimestamp()


        def checkIfHomeExists():
            # Get associated partner's (contact/home/compnay) data
            partnerId = self.read()[0]['partner_id'][0]
            
            # Check if the contact exists in lindera backend
            homeData = backend_client.getHome(partnerId).json()
            if homeData['total'] == 0 and len(homeData['data']) == 0:
                raise osv.except_osv(('Error!'), ('The associated partner does not exist in Lindera database, please create it first'))
            else:
                mongoId = homeData['data'][0]['_id']
                return mongoId
        
        def update(id, field):
            updatedField = {
                'subscriptionEndDate': field
            }
            return backend_client.updateHome(id, updatedField)

        if name == '8 W-Test live' or name == 'Einführung':
            mID = checkIfHomeExists()

            futureTs = cts + ( 60 * 60 * 24 * 70 )
            expirationDate = datetime.fromtimestamp(futureTs).isoformat()
            update(mID, expirationDate)
        
        if name == 'On hold':
            mID = checkIfHomeExists()

            pastTs = cts - ( 60 * 60 * 24 )
            expirationDate = datetime.fromtimestamp(pastTs).isoformat()
            update(mID, expirationDate)

        return result


class LinderaContacts(models.Model):
    _inherit = 'res.partner'

    @api.model
    def create(self, val):
        res = super(LinderaContacts, self).create(val)

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
                raise osv.except_osv(('Error!'), ('These tags are not allowed to be used together'))
            if len(tags) == 0:
                raise osv.except_osv(('Error!'), ('Please select a tag'))
            elif(len(typeOfHome) == 1):
                typeOfHome = typeOfHome[0]
            else:
                return res

            payload = preparePayload(typeOfHome, res)

            if not parentId:
                apiResponse = backend_client.postHome(payload).json()
                # if apiResponse['confirmation']:
                raise osv.except_osv(('Error!'), (apiResponse))

            # else:
            #     if addressType and addressType == 'contact':
            #         raise osv.except_osv(('Error!'), ('Address is missing'))

            #     parent = backend_client.getHome(parentId).json()
            #     # If the resource (home/company/contact) is not in lindera backend, then create it
            #     if parent and parent['total'] == 0:
            #         home = backend_client.postHome(payload).json()
            #         parentData = self.env['res.partner'].search(
            #             [('id', '=', parentId)])
            #         if parentData:
            #             if(typeOfHome == 'Einrichtung'):
            #                 payload = preparePayload('Träger', parentData)
            #             elif(typeOfHome == 'Träger'):
            #                 payload = preparePayload('Gruppe', parentData)

            #             parentId = backend_client.postHome(payload).json()['data']['_id']

            #             children = [home['data']['_id']]

            #     # If the resource (home/company/contact) exists in lindera backend, then update the children field with the newly created resource ID
            #     elif parent and parent['total'] >= 1:
            #         role = parent['data'][0]['role']
            #         if (typeOfHome == 'Einrichtung' and (role == 'home' or role == 'organization' )) or (typeOfHome == 'Träger' and (role == 'home' or role == 'company' )):
            #             raise osv.except_osv(('Error!'), ('This contact can not be assigned as parent'))
                
                    
            #         home = backend_client.postHome(payload).json()
            #         children = parent['data'][0]['children']
            #         children = list(map(lambda child: child['_id'], children))

            #         newHomeId = home['data']['_id']
            #         children.append(newHomeId)

            #         parentId = parent['data'][0]['_id']

            #     updatedField = {
            #         'children': children
            #     }
            #     backend_client.updateHome(parentId, updatedField)

        return res


class linderaApi(models.Model):
    _name = "lindera.api"
    _description = "lindera api related info"
