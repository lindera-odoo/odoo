from odoo import models, fields, api


class PromoCode(models.Model):
    _name = 'lindera.promocode'
    _description = 'promo code'

    code = fields.Char('Code', required=True)
    sales_partner_id = fields.Many2one('res.partner', string='Sales Partner')
