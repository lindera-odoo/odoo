from odoo import models, fields, api

from . import backend_client


class linderaBackendID(models.Model):
    """
    Foreign ID placeholder
    """
    
    _name = 'lindera.backend.id'
    
    home_id = fields.Text('home_id')
    
    contact_id = fields.Many2one('res.partner', required=True, ondelete='cascade')
    
    @api.one
    def write(self, vals):
        out = super().write(vals)
        backendClient = backend_client.BackendClient.setupBackendClient(self)
        if 'home_id' in vals.keys():
            home_id = vals['home_id']
            backendClient.updateHome(self.home_id, {'odooID': None})
        else:
            home_id = self.home_id
            
        if 'contact_id' in vals.keys():
            odoo_id = vals['contact_id']
        else:
            odoo_id = self.contact_id
            
        backendClient.updateHome(home_id, {'odooID': odoo_id.id})
        return out