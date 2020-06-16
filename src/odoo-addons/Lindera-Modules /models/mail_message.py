from odoo import models, fields, api

import logging
_logger = logging.getLogger(__name__)


class linderaMail(models.Model):
    _inherit = 'mail.message'
    o365ID = fields.Char('o365ID')
    o365ConversationID = fields.Char('o365ConversationID')
    
    @api.model
    def create(self, val):
        res = super(linderaMail, self).create(val)

        _logger.warning(self.model)
        if self.model == 'helpdesk.ticket':
            if self.res_id:
                _logger.warning(self.res_id)
                
        
        return res