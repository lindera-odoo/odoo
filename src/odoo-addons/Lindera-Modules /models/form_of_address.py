from odoo import models, fields, api

from . import backend_client


class linderaBackendID(models.Model):
    """
    Foreign ID placeholder
    """
    
    _name = 'lindera.address'
    
    first_name = fields.Char('first_name')
    last_name = fields.Char('last_name')
    form_of_address = fields.Char('form_of_address')
    
    contact_id = fields.Many2one('res.partner', required=True, ondelete='cascade')