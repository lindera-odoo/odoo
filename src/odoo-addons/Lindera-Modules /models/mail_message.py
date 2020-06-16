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
    
        _logger.warning('Logging Message create')
        _logger.warning(res.model)
        _logger.warning(res.body)
        if res.model == 'helpdesk.ticket':
            if res.res_id:
                _logger.warning(res.res_id)
        _logger.warning('Logging Message create end')
    
    
        return res

    @api.model
    def write(self, val):
        res = super(linderaMail, self).write(val)
    
        _logger.warning('Logging Message write')
        _logger.warning(self.model)
        _logger.warning(self.body)
        if self.model == 'helpdesk.ticket':
            if self.res_id:
                _logger.warning(self.res_id)
        _logger.warning('Logging Message write end')
    
        return res