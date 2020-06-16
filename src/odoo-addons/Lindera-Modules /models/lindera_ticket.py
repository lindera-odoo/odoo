from odoo import models, fields, api
import json
import logging
_logger = logging.getLogger(__name__)

class LinderaTicket(models.Model):
    _inherit = 'helpdesk.ticket'
    _logger.warning('inherited ticket')

    @api.model
    def write(self, values):
        _logger.warning('Dumping Data for Logs since odoo never heard from debugging.... WRITING')
        _logger.warning(str(values))
        res = super(LinderaTicket, self).write(values)
        _logger.warning('More Dumping')
        _logger.warning(str(res))
        _logger.warning('Dumping Messages')
        _logger.warning(str(self.message_ids))
        
        if '@lindera' in self.partner_email and 'partner_email' not in values.keys():
            for message in self.message_ids:
                try:
                    _logger.warning(message)
                    _logger.warning(message.body)
                    test = json.loads(message.body)
                except:
                    pass
        
        _logger.warning('Dumping Done')
        return res