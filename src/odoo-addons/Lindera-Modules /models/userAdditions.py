from odoo import models, fields, api

class LinderOfficeUser(models.Model):
    """
    Add more fields and functions to the user
    """
    _inherit = 'res.users' 

    auth_state = fields.Char('auth_state')
    auth_token = fields.Char('auth_token')
    auth_url = fields.Char('auth_url')

    @api.multi
    def write(self, values):
        if 'email' in values.keys() or 'login' in values.keys():
            values['auth_token'] = ''
        return super(LinderOfficeUser, self).write(values)

