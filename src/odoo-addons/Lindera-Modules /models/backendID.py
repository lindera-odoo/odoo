from odoo import models, fields, api

from . import backend_client


class linderaBackendID(models.Model):
    """
    Foreign ID placeholder
    """
    
    _name = 'lindera.backend.id'
    
    home_id = fields.Text('home_id')
    
    contact_id = fields.Many2one('res.partner', required=True, ondelete='cascade')