from odoo import models, fields, api


class LinderaSubscription(models.Model):
    """
    Add more fields and functions to the leads
    """
    _inherit = 'sale.subscription'
    
    invoice_adress = fields.Many2one('res.partner', string='Rechnungsaddresse',  index=True,
                                    help="Kontakt an den die Rechnung verschickt werden soll")