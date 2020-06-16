from odoo import models, fields, api
import json
import logging
_logger = logging.getLogger(__name__)

class LinderaTicket(models.Model):
    _inherit = 'helpdesk.ticket'

    @api.onchange('message_ids')
    def _onchange_messages(self):
        _logger.warning('Dumping Data for Logs since odoo never heard from debugging.... Message')
        if '@lindera' in self.partner_email:
            for message in self.message_ids:
                try:
                    _logger.warning(message)
                    _logger.warning(message.body)
                    test = json.loads(message.body)
                except:
                    pass
        _logger.warning('Dumping Done')