from odoo import models, fields, api
from . import backend_client
from datetime import datetime
from openerp.osv import osv


def getCurrentTimestamp():
    return datetime.now().timestamp().__round__()


class LinderaCRM(models.Model):
    _inherit = 'crm.lead'

    def generate(self):
        leads = self.env['crm.lead'].search([])
        targetLeads = []
        partnerIds = []

        for lead in leads:
            tag_ids = lead.tag_ids
            for tag_id in tag_ids:
                if tag_id.name == 'Kunde / Pflegeberatung' and (lead.stage_id.name == 'Live' or lead.stage_id.name == 'In Evaluation'):
                    targetLeads.append(lead)
        if targetLeads:
            for targetLead in targetLeads:
                data = targetLead.read()[0]
                partner = data['partner_id']
                if partner:
                    partnerId = partner[0]
                    contact = self.env['res.partner'].search(
                        [('id', '=', partnerId)])

                    isCompany = contact.is_company
                    parentCompany = contact.parent_id
                    parentCompanyId = parentCompany.id

                    if isCompany:
                        targetContactId = partnerId
                    else:
                        targetContactId = parentCompanyId

                    partnerIds.append(targetContactId)
        if partnerIds:
            bClient = backend_client.BackendClient.setupBackendClient(
                self)
            bClient.notifyBackendToCreateReport(partnerIds)

    def checkIfHomeExists(self, contact):
        isCompany = contact.is_company

        if not isCompany:
            parentCompany = contact.parent_id
            parentCompanyId = parentCompany.id
            if not parentCompanyId:
                raise osv.except_osv(
                    ('Error!'), ('Associated contact should have a parent company'))
            else:
                homeData = contact.isHomeExistsInLinderaDB(parentCompanyId)
                if homeData:
                    mongoId = homeData['data'][0]['_id']
                    return mongoId
                else:
                    result = parentCompany.createHomeInLinderaDB()
                    mongodbId = result['data']['_id']
                    return mongodbId

        else:
            homeData = contact.isHomeExistsInLinderaDB(contact.id)
            if homeData:
                mongoId = homeData['data'][0]['_id']
                return mongoId
            else:
                result = contact.createHomeInLinderaDB()
                mongodbId = result['data']['_id']
                return mongodbId

    def getSubscriptionEndDate(self, contact):
        # except for the case of running locally, where we are not able to install the subscription module
        try:
            subscriptions = self.env['sale.subscription'].search(
                [('partner_id', '=', contact.id)])
        except:
            return False
        if subscriptions:
            subscription = subscriptions[0]
            for sub in subscriptions:
                if sub.date > subscription.date:
                    subscription = sub
            return subscription
        else:
            return False

    @api.multi
    def write(self, vals):
        previouse_stage = self.stage_id
        result = super(LinderaCRM, self).write(vals)

        if 'stage_id' not in vals:
            return result

        id = vals['stage_id']
        stage = self.env['crm.stage'].search([('id', '=', id)])
        name = stage.name
        # Get the current timestamp in seconds
        cts = getCurrentTimestamp()
        previouse_stage_name = previouse_stage.name

        # Read the associated contact
        data = self.read()[0]
        partner = data['partner_id']
        if partner:
            partnerId = partner[0]
            contact = self.env['res.partner'].search(
                [('id', '=', partnerId)])
        else:
            raise osv.except_osv(
                ('Error!'), ('CRM card does not have a contact'))

        mongoId = self.checkIfHomeExists(contact)
        if mongoId:
            if stage.allow_subscription:
                isCompany = contact.is_company
    
                if isCompany:
                    targetContact = contact
                else:
                    parentCompany = contact.parent_id
                    targetContact = parentCompany
    
                subscription = self.getSubscriptionEndDate(
                    targetContact)
    
                if subscription:
                    if subscription.date:
                        subEndDate = subscription.date.isoformat()
                    else:
                        futureTs = cts + (stage.subscription_duration)
                        subEndDate = datetime.fromtimestamp(
                            futureTs).isoformat()
    
                else:
                    pastTs = cts - (60 * 60 * 24)
                    subEndDate = datetime.fromtimestamp(pastTs).isoformat()
    
                updatedField = {
                    'subscriptionEndDate': subEndDate
                }
                contact.updateHome(mongoId, updatedField)
                
                for user in self.create_users:
                    user.createUser(mongoId)

            else:
                futureTs = cts - (60 * 60 * 24)
                expirationDate = datetime.fromtimestamp(
                    futureTs).isoformat()
                contact.updateHome(mongoId, {'subscriptionEndDate': expirationDate})
        else:
            return result

        return result
