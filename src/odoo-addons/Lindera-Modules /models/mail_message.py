import sentry_sdk

from odoo import models, fields, api
from odoo.exceptions import UserError
from odoo.osv import osv
from .sentrySingleton import sentrySingleton
import json
import re
import logging
_logger = logging.getLogger(__name__)


class linderaMail(models.Model):
    _inherit = 'mail.message'
    o365ID = fields.Char('o365ID')
    o365ConversationID = fields.Char('o365ConversationID')
    
    @api.model
    def create(self, val):
        if 'model' in val.keys() and val['model'] == 'helpdesk.ticket':
            if 'res_id' in val.keys() and val['res_id']:
                ticket = self.env['helpdesk.ticket'].browse(val['res_id'])
                if '@lindera' in str(ticket.partner_email) and 'body' in val.keys() and val['body']:
                    sentryClient = self.env['ir.config_parameter'].get_param(
                        'lindera.raven_client')
                    sentrySingle = sentrySingleton(sentryClient)
                    with sentry_sdk.push_scope() as scope:
                        scope.set_extra('debug', False)
                        try:
                            clean = re.sub('<.*?>', '', val['body']).replace('&quot;', '"').replace('\n', ' ')
                            data = json.loads(clean)
                            partner = self.env['res.partner'].search([('email', '=', data['email'])])
                            if not partner:
                                create_data = {
                                    'name': data['name'],
                                    'email': data['email']
                                }
                                if 'street' in data.keys(): create_data['street'] = data['address']
                                if 'zip_city' in data.keys(): create_data['zip'] = data['zip_city'].split(' ')[0]
                                if 'zip_city' in data.keys() and ' ' in data['zip_city']:
                                    create_data['city'] = data['zip_city'].split(' ')[1]
                
                                partner = self.env['res.partner'].create(create_data)
                            else:
                                partner = partner[0]
                            ticket.partner_email = partner.email
                            ticket.partner_id = partner.id
            
                            val['message_type'] = 'comment'
                            val['subtype'] = 'note'
            
                            ticket.env.cr.commit()
                        except json.JSONDecodeError:
                            pass
                        except Exception as e:
                            sentry_sdk.capture_exception(e)
                            raise UserError('Error While Syncing!' + str(e))
                    
        res = super(linderaMail, self).create(val)
        return res