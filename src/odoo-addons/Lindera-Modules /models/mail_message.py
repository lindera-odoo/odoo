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
        res = super(linderaMail, self).create(val)
    
        if res.model == 'helpdesk.ticket':
            if res.res_id:
                ticket = self.env['helpdesk.ticket'].browse(res.res_id)
                if '@lindera' in str(ticket.partner_email) and res.body:
                    ravenClient = self.env['ir.config_parameter'].get_param(
                        'lindera.raven_client')
                    ravenSingle = ravenSingleton(ravenClient)
                    try:
                        clean = re.sub('<.*?>', '', res.body)
                        data = json.loads(clean)
                        partner = self.env['res.partner'].search([('email', '=', data['email'])])
                        if not partner:
                            create_data = {
                                'name': data['contact_name'],
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
                        
                        res.message_type = 'notification'
                        
                        self.env.cr.commit()
                    except json.JSONDecodeError:
                        pass
                    except Exception as e:
                        ravenSingle.Client.captureMessage(e)
                        raise osv.except_osv('Error While Syncing!', str(e))
    
        return res