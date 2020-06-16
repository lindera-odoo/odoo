from odoo import models, fields, api

class LinderaTicket:
    _inherit = 'helpdesk.ticket'

    @api.model
    def create(self, val):
        print('Dumping Data for Logs since odoo never heard from debugging....')
        print(val)
        res = super(LinderaTicket, self).create(val)
        print('More Dumping')
        print(res)
        print('Dumping Done')
        return res