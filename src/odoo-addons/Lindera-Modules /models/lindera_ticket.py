from odoo import models, fields, api

import logging
_logger = logging.getLogger(__name__)

class LinderaTicket(models.Model):
    _inherit = 'helpdesk.ticket'
    _logger.warning('inherited ticket')

    @api.model
    def create(self, val):
        _logger.warning('Dumping Data for Logs since odoo never heard from debugging....')
        _logger.warning(str(val))
        res = super(LinderaTicket, self).create(val)
        _logger.warning('More Dumping')
        _logger.warning(str(res))
        _logger.warning('Dumping Done')
        return res