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
                    partnerIds.append(partnerId)
        if partnerIds:
            bClient = self.setupBackendClient()
            bClient.notifyBackendToCreateReport(partnerIds)

    def updateHome(self, mongodbId, field):
        updatedField = {
            'subscriptionEndDate': field
        }
        bClient = self.setupBackendClient()
        return bClient.updateHome(mongodbId, updatedField)

    def setupBackendClient(self):
        url = self.env['ir.config_parameter'].get_param('lindera.backend')
        token = self.env['ir.config_parameter'].get_param(
            'lindera.internal_authentication_token')
        ravenClient = self.env['ir.config_parameter'].get_param(
            'lindera.raven_client')

        if (url and token and ravenClient):
            backendClient = backend_client.BackendClient(
                url, token, ravenClient)
            return backendClient
        else:
            raise osv.except_osv(
                ('Error!'), ('Please, setup system parameters for lindera backend'))

    def checkIfHomeExists(self):
        # Get associated partner's (contact/home/compnay) data
        data = self.read()[0]
        partner = data['partner_id']
        if partner:
            partnerId = partner[0]
            # Check if the contact exists in lindera backend
            bClient = self.setupBackendClient()
            homeData = bClient.getHome(partnerId).json()
            if homeData['total'] == 0 and len(homeData['data']) == 0:
                contact = self.env['res.partner'].search(
                    [('id', '=', partnerId)])
                # Create home in lindera backend
                payload = {
                    'name': contact.name,
                    'city': contact.city,
                    'street': contact.street,
                    'zip': contact.zip,
                    'role': 'home',
                    'odooID': contact.id
                }

                result = bClient.postHome(payload).json()
                return result['data']['_id']

            else:
                mongoId = homeData['data'][0]['_id']
                return mongoId

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

        if name == 'Salestermin geplant':
            mongoId = self.checkIfHomeExists()
            if mongoId:
                futureTs = cts + (60 * 60 * 24 * 120)
                expirationDate = datetime.fromtimestamp(futureTs).isoformat()
                self.updateHome(mongoId, expirationDate)
            else:
                return result

        if name == 'Bereit für Einführung' or name == 'In Evaluation' or name == 'Einführung in Planung' or name == 'Live' or name == 'Angebot gezeichnet' or name == 'Intergration':
            if previouse_stage_name == 'Salestermin geplant':
                return result

            mongoId = self.checkIfHomeExists()
            if mongoId:
                futureTs = cts + (60 * 60 * 24 * 12000)
                expirationDate = datetime.fromtimestamp(
                    futureTs).isoformat()
                self.updateHome(mongoId, expirationDate)
            else:
                return result

        if name == 'On hold':
            mongoId = self.checkIfHomeExists()
            if mongoId:
                pastTs = cts - (60 * 60 * 24)
                expirationDate = datetime.fromtimestamp(pastTs).isoformat()
                self.updateHome(mongoId, expirationDate)
            else:
                return result

        return result
