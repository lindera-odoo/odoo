from odoo import models, fields, api
from openerp.osv import osv
from .ravenSingleton import ravenSingleton
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
            if 'res_id' in val.keys() and  val['res_id']:
                ticket = self.env['helpdesk.ticket'].browse(val['res_id'])
                _logger.warning('Mail Receiver: Ding')
                _logger.warning('Mail Receiver: ' + str(ticket.partner_email))
                if '@lindera' in str(ticket.partner_email) and 'body' in val.keys() and val['body']:
                    ravenClient = self.env['ir.config_parameter'].get_param(
                        'lindera.raven_client')
                    ravenSingle = ravenSingleton(ravenClient)
    
                    _logger.warning('Mail Receiver: Dong')
                    try:
                        clean = re.sub('<.*?>', '', val['body'])
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
        
                        self.env.cr.commit()
                    except json.JSONDecodeError:
                        pass
                    except Exception as e:
                        ravenSingle.Client.captureMessage(e)
                        raise osv.except_osv('Error While Syncing!', str(e))
                    
        res = super(linderaMail, self).create(val)
        return res