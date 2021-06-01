from odoo import models, fields, api


class linderaConversationsCleaner(models.Model):
    _name = 'lindera.office.mail.cleaner'
    
    @api.model
    def cleanConversations(self):
        changed = True
        
        while changed:
            changed = False
            to_check = self.env['mail.message'].search([('o365ConversationID', '!=', None)])
            
            for mail in to_check:
                if mail.parent_id is not None:
                    if mail.model != mail.parent_id.model or \
                            mail.res_id != mail.parent_id.res_id or \
                            mail.subtype_id.name == 'Note':
                        changed = True
                        mail.o365ConversationID = None
                        mail.parent_id = None
            self.env.cr.commit()
        
        changed = True
        
        while changed:
            changed = False
            to_check = self.env['mail.message']\
                .search([('o365ConversationID', '=', None)])\
                .sorted(key=lambda mail: mail.date)
            
            for mail in to_check:
                if mail.parent_id is None:
                    prev_mail = self.env['mail.message'].search(
                        [('o365ConversationID', '!=', None),
                         ('model', '=', mail.model),
                         ('res_id', '=', mail.res_id),
                         ('date', '<', mail.date)]).sorted(key=lambda mail: mail.date)
                    if prev_mail:
                        changed = True
                        mail.parent_id = prev_mail[-1]
                        if not mail.subtype_id.name == 'Note':
                            mail.o365ConversationID = prev_mail[-1].o365ConversationID
                        self.env.cr.commit()
