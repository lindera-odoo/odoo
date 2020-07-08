from odoo import http
from openerp.osv import osv


class Contact(http.Controller):
    @http.route('/homes/x', auth='user')
    def createStructure(self, **kwargs):
        contact = http.request.env['res.partner']
        raise osv.except_osv(
            ('Error!'), ('I get called'))
