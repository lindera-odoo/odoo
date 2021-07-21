from odoo import models, fields

class LinderOfficeUser(models.Model):
    """
    Add more fields and functions to the stages
    """
    _inherit = 'crm.stage'

    allow_subscription = fields.Boolean('allow_subscription')
    subscription_duration = fields.Integer('subscription_duration')