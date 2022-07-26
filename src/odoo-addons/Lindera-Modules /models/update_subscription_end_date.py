from odoo import models, fields, api


class linderaBackendSubscriptionUpdater(models.Model):
    _name = 'lindera.backend.subscription'
    
    @api.model
    def clean_subscription_end_date(self):
        to_clean = self.env['crm.lead'].search([])
        for lead in to_clean:
            if lead.partner_id.homeID is not None and lead.end_date and lead.stage_id.allow_subscription:
                lead.partner_id.updateHome(lead.partner_id.homeID,
                                           {
                                               'subscriptionEndDate': lead.end_date.isoformat()
                                           })
