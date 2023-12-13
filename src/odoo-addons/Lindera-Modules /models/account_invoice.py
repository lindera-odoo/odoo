import logging

from odoo import models, fields, api
from odoo.osv import osv

_logger = logging.getLogger(__name__)

class LinderaInvoice(models.Model):
    _inherit = "account.move"
    
    invoice_adress = fields.Many2one('res.partner', string='Rechnungs E-mail', index=True,
                                     help="Kontakt an den die Rechnung verschickt werden soll")
    def setup_lead(self):
        # search for the user used in the webshop
        user = self.env['res.users'].search([('partner_id', '=', self.partner_id.id), ('share', '=', True)])
        
        # update contact if this invoice came through the webshop
        if user:
            # update partner if needed
            if not self.partner_id.is_company:
                if not self.partner_id.parent_id:
                    self.partner_id.is_company = True
                    is_einrichtung = False
                    for cat in self.partner_id.category_id:
                        if cat.name == 'Einrichtung':
                            is_einrichtung = True
                    if not is_einrichtung:
                        cat = self.env['res.partner.category'].search([('name', '=', 'Einrichtung')])
                        self.partner_id.category_id += cat
            self.env.cr.commit()
            #create and handle lead
            lead = self.env['crm.lead'].search([('partner_id', '=', self.partner_id.id)])
            if not lead:
                lead = self.env['crm.lead'].create({
                    'name': self.partner_id.display_name,
                    'partner_id': self.partner_id.id,
                    'active': True,
                    'email_from': self.partner_id.email,
                    'contact_name': self.partner_id.name,
                    'type': 'opportunity',
                })
                self.env.cr.commit()
            else:
                lead = lead[0]
            
            if self.partner_id not in lead.create_users:
                lead.create_users += self.partner_id
            live = self.env['crm.stage'].search([('name', '=', 'Live')])
            if live:
                live = live[0]
            else:
                raise osv.except_osv(('Error!'), ('Webshop not setup correctly! CRM needs a "Live" stage! Please contact support with this error message.'))
            lead.stage_id = live.id
            self.env.cr.commit()
        

    @api.model
    def create(self, values):
        obj = super(LinderaInvoice, self).create(values)
        if obj.state == 'posted':
                obj.setup_lead()
        
        if not self.invoice_adress:
            subscription = self.env['sale.subscription'].search([('code', '=', self.invoice_origin)])
            if subscription:
                self.invoice_adress = subscription.invoice_adress
        
        return obj

    @api.model_create_multi
    def create(self, vals_list):
        objs = super(LinderaInvoice, self).create(vals_list)
        
        for index, invoice in enumerate(objs):
            if invoice.state == 'posted':
                    invoice.setup_lead()
            
            if not invoice.invoice_adress and 'invoice_adress' not in vals_list[index].keys():
                subscription = self.env['sale.subscription'].search([('code', '=', self.invoice_origin)])
                if subscription:
                    invoice.invoice_adress = subscription.invoice_adress
                
        return objs

    def write(self, values):
        status = super(LinderaInvoice, self).write(values)
        for invoice in self:
            if invoice.state == 'posted':
                    invoice.setup_lead()
            
            _logger.info('checking if invoice adress shall be updated')
            if not invoice.invoice_adress and 'invoice_adress' not in values.keys():
                _logger.info('looking for subscription via ' + invoice.invoice_origin)
                subscription = self.env['sale.subscription'].search([('code', '=', invoice.invoice_origin)])
                if subscription:
                    _logger.info('found subscription')
                    invoice.invoice_adress = subscription.invoice_adress
        
        return status
