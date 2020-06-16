from odoo import models, fields, api
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
    
        _logger.warning('Logging Message create')
        _logger.warning(res.model)
        _logger.warning(res.body)
        if res.model == 'helpdesk.ticket':
            if res.res_id:
                _logger.warning(res.res_id)
                ticket = self.env['helpdesk.ticket'].browse(res.res_id)
                _logger.warning(ticket.partner_email)
                if '@lindera' in ticket.partner_email:
                    try:
                        clean = re.sub('<.*?>', '', self.body)
                        _logger.warning(clean)
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
                        _logger.warning(partner)
                        ticket.partner_email = partner.email
                        ticket.partner_id = partner.id
                        self.env.cr.commit()
                    except:
                        pass

                
        _logger.warning('Logging Message create end')
    
    
        return res