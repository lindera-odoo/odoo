import logging

from odoo import models, fields, api
from odoo.osv import osv

_logger = logging.getLogger(__name__)

class LinderaInvoice(models.Model):
    _inherit = "account.move"

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
        
        return obj

    @api.model_create_multi
    def create(self, vals_list):
        objs = super(LinderaInvoice, self).create(vals_list)
        
        for invoice in objs:
            if invoice.state == 'posted':
                    invoice.setup_lead()
                
        return objs

    def write(self, values):
        status = super(LinderaInvoice, self).write(values)
        for invoice in self:
            if invoice.state == 'posted':
                    invoice.setup_lead()
        
        return status
    
    def message_post_with_template(self, template_id, email_layout_xmlid=None, auto_commit=False, **kwargs):
        # if not kwargs.get('composition_mode'):
        #
        #     kwargs['composition_mode'] == 'mass_mail'
        
        _logger.info('Sending with Template intercepted! Composition mode: ' + str(kwargs.get('composition_mode')))
        
        return super(LinderaInvoice, self).message_post_with_template(template_id, email_layout_xmlid, auto_commit, **kwargs)
