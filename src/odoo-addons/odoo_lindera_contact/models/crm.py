from odoo import models, fields, api
from . import backend_client
from datetime import datetime
from openerp.osv import osv


def getCurrentTimestamp():
    return datetime.now().timestamp().__round__()


class LinderaCRM(models.Model):
    _inherit = 'crm.lead'

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
                partnerData = self.env['res.partner'].search(
                    [('id', '=', partnerId)])

                payload = {
                    'name': partnerData.name,
                    'city': partnerData.city,
                    'street': partnerData.street,
                    'zip': partnerData.zip,
                    'role': 'organization',
                    'odooID': partnerData.id
                }

                data = bClient.postHome(payload).json()
                return data['data']['_id']

            else:
                mongoId = homeData['data'][0]['_id']
                return mongoId

    @api.multi
    def write(self, vals):
        result = super(LinderaCRM, self).write(vals)

        if 'stage_id' not in vals:
            return result

        id = vals['stage_id']
        stage = self.env['crm.stage'].search([('id', '=', id)])
        name = stage.name
        # Get the current timestamp in seconds
        cts = getCurrentTimestamp()

        if name == 'Salestermin geplant' or name == 'Terminplanung 8 W-Test' or name == '8 W-Test':
            mongoId = self.checkIfHomeExists()
            futureTs = cts + (60 * 60 * 24 * 120)
            expirationDate = datetime.fromtimestamp(futureTs).isoformat()
            self.updateHome(mongoId, expirationDate)

        elif name == 'Bereit für Einführung' or name == 'In Evaluation' or name == 'Einführung in Planung' or name == 'Live':
            mongoId = self.checkIfHomeExists()
            futureTs = cts + (60 * 60 * 24 * 12000)
            expirationDate = datetime.fromtimestamp(futureTs).isoformat()
            self.updateHome(mongoId, expirationDate)

        else:
            mongoId = self.checkIfHomeExists()
            pastTs = cts - (60 * 60 * 24)
            expirationDate = datetime.fromtimestamp(pastTs).isoformat()
            self.updateHome(mongoId, expirationDate)

        return result
