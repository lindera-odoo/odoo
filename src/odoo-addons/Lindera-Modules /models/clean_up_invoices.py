from odoo import models, fields, api


class linderaConversationsCleaner(models.Model):
    _name = 'lindera.invoice.cleaner'
    
    @api.model
    def cleanInvoices(self):
        to_send = self.env['account.move'].search([('state', '==', 'posted'), ('is_move_sent', '==', False)])
        to_send.is_move_sent = True
        self.env.cr.commit()