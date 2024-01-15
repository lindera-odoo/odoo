from odoo import models, fields, api

from . import backend_client

form_of_address_selection_options = [
    ('woman', 'Sehr geehrte Frau'),
    ('man', 'Sehr geehrter Herr'),
    ('mixed', 'Sehr geehrte Damen und Herren')
]

class linderaAddress(models.Model):
    
    _name = 'lindera.address'
    
    first_name = fields.Char('first_name')
    last_name = fields.Char('last_name')
    form_of_address = fields.Selection(selection=form_of_address_selection_options)
    
    contact_id = fields.Many2one('res.partner', required=True, ondelete='cascade')