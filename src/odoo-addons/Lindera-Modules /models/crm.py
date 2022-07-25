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

    @api.multi
    def write(self, vals):
        previouse_stage = self.stage_id
        result = super(LinderaCRM, self).write(vals)
        
        if 'end_date' in vals:
            for lead in result:
                if lead.partner_id.homeID is not None and lead.end_date:
                    updatedField = {
                        'subscriptionEndDate': result.end_date.isoformat()
                    }
                    lead.partner_id.updateHome(lead.partner_id.homeID, updatedField)
        
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
                if data.end_date:
                    updatedField = {
                        'subscriptionEndDate': data.end_date.isoformat()
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
