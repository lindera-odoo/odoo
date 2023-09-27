import os
import logging
import re
import base64
from io import BytesIO

import sentry_sdk

from odoo import models, fields, api
from O365 import Account
from .odooTokenStore import odooTokenStore
from odoo import tools
from odoo.addons.base.models.ir_mail_server import MailDeliveryException
from .sentrySingleton import sentrySingleton
import datetime
import dateutil
import time

_logger = logging.getLogger(__name__)


class linderaMail(models.Model):
    _inherit = 'mail.mail'

    def send(self, auto_commit=False, raise_exception=False):
        CLIENT_ID = self.env['ir.config_parameter'].get_param('lindera.client_id')
        CLIENT_SECRET = self.env['ir.config_parameter'].get_param('lindera.client_secret')
        sentryClient = self.env['ir.config_parameter'].get_param('lindera.raven_client')
        sentrySingle = sentrySingleton(sentryClient)

        ids = self.ids

        for id in ids:
            mail = self.browse(id)
            email_list = []
            if mail.email_to:
                email_list.append(tools.email_split(mail.email_to))
            for partner in mail.recipient_ids:
                email_list.append(partner.email)

            allowtosend = True
            blacklistMails = ['service@lindera.de', 'support@lindera.odoo.com', 'vendor-bills@lindera.odoo.com', 'invoices@lindera.de']
            channels = self.env['crm.team'].search([])

            for channel in channels:
                if len(channel.alias_id.name_get()) > 0:
                    blacklistMails.append(channel.alias_id.name_get()[0][1])

            for email in email_list:
                if email in blacklistMails:
                    allowtosend = False
                    break

            user = self.env['res.users'].search([("partner_id", "=", mail.author_id.id), ('share', '=', False)])
            _logger.info('Sending mail for user' + str(mail.author_id.id))
            if user:
                user = user[0]
                _logger.info('Found user' + str(user.id))
            else:
                _logger.info('Did not find user')
                # try looking for an alternative user specified by the from field instead of from the author
                _logger.info('Looking for new user via email from ' + str(tools.email_normalize(mail.email_from)))
                user = self.env['res.users'].search([("login", "=", tools.email_normalize(mail.email_from)), ('share', '=', False)])
                if user:
                    _logger.info('Found new user')
                    user = user[0]
                else:
                    _logger.info('Did not find new user')
                    return super(linderaMail, mail).send(auto_commit=auto_commit, raise_exception=raise_exception)
            
            token_backend = odooTokenStore(user)
            _logger.info('Checking token')
            if not token_backend.check_token():
                _logger.info('No token')
                # try looking for an alternative user specified by the from field instead of from the author
                _logger.info('Looking for new user via email from' + str(tools.email_normalize(mail.email_from)))
                user = self.env['res.users'].search([("login", "=", tools.email_normalize(mail.email_from)), ('share', '=', False)])
                if user:
                    _logger.info('Found new user')
                    user = user[0]
                    token_backend = odooTokenStore(user)
                else:
                    _logger.info('Did not find new user')
                    return super(linderaMail, mail).send(auto_commit=auto_commit, raise_exception=raise_exception)
            
            if token_backend.check_token() and allowtosend:
                with sentry_sdk.push_scope() as scope:
                    scope.set_extra('debug', False)
                    try:
                        account = Account((CLIENT_ID, CLIENT_SECRET), token_backend=token_backend)
                        if account.is_authenticated:
                            IrAttachment = self.env['ir.attachment']
                            # remove attachments if user send the link with the access_token
                            body = mail.body_html or ''
                            attachments = mail.attachment_ids
                            for link in re.findall(r'/web/(?:content|image)/([0-9]+)', body):
                                attachments = attachments - IrAttachment.browse(int(link))
    
                            # load attachment binary data with a separate read(), as prefetching all
                            # `datas` (binary field) could bloat the browse cache, triggerring
                            # soft/hard mem limits with temporary data.
                            attachments = [(BytesIO(base64.b64decode(a['datas'])), a['display_name']) for a in attachments.sudo().read(['display_name', 'datas']) if a['datas'] is not False]
    
                            mailbox = account.mailbox()
    
                            # specific behavior to customize the send email for notified partners
                            email_list = []
                            if mail.email_to:
                                values = mail._send_prepare_values()
                                values['email_to'] = tools.email_split(mail.email_to)
                                values['partner_id'] = None
                                email_list.append(values)
                            for partner in mail.recipient_ids:
                                values = mail._send_prepare_values(partner=partner)
                                values['partner_id'] = partner
                                values['email_to'] = partner.email
                                email_list.append(values)
    
                            same = True
                            body = email_list[0]['body']
                            mails = []
                            partners = []
                            for email in email_list:
                                same = same and (email['body'] == body)
                                mails.append(email['email_to'])
                                partners.append(email['partner_id'])
                            if same:
                                value = email_list[0]
                                value['email_to'] = mails
                                value['partner_id'] = partners
                                email_list = [value]
    
                            process_pids = []
                            for email in email_list:
                                process_pid = email.pop("partner_id", None)
                                
                                is_external = True
                                if process_pid is not None:
                                    for pid in process_pid:
                                        target_user = self.env['res.users'].search([("partner_id", "=", pid.id),
                                                                                    ('share', '=', False)])
                                        if target_user:
                                            is_external = False
                                
                                # set data
                                message = mailbox.new_message()
                                is_reply = False
                                if mail.subtype_id.name != 'Note':
                                    # find the most likely candidate for the parent
                                    prev_mail = self.env['mail.message'].search(
                                        [('o365ConversationID', '!=', None),
                                         ('model', '=', mail.model),
                                         ('res_id', '=', mail.res_id),
                                         ('message_type', '=', mail.message_type),
                                         ('subtype_id', '=', mail.subtype_id.id),
                                         ('id', '!=', mail.mail_message_id.id),
                                         ('partner_ids', '=', mail.recipient_ids.id)])
                                    
                                    for pid in process_pid:
                                        prev_mail += self.env['mail.message'].search(
                                            [('o365ConversationID', '!=', None),
                                             ('model', '=', mail.model),
                                             ('res_id', '=', mail.res_id),
                                             ('id', '!=', mail.mail_message_id.id),
                                             ('author_id', '=', pid.id)])
                                    prev_mail = prev_mail.sorted(key=lambda element: element.date)
                                    
                                    if prev_mail:
                                        mail.parent_id = prev_mail[-1]
    
                                    if mail.parent_id.o365ConversationID:
                                        # find the most recent entry of this conversation (might be the reply, which does not fit the most likely)
                                        prev_mail = self.env['mail.message'].search(
                                            [('o365ConversationID', '=', mail.parent_id.o365ConversationID),
                                             ('model', '=', mail.model),
                                             ('res_id', '=', mail.res_id),
                                             ('id', '!=', mail.mail_message_id.id)]).sorted(key=lambda element: element.date)
                                        prev_mail = prev_mail.sorted(key=lambda element: element.date)
                                        if prev_mail:
                                            mail.parent_id = prev_mail[-1]
                                            try:
                                                oldMessage = mailbox.get_message(mail.parent_id.o365ID)
                                                replyMessage = oldMessage.reply()
                                                if replyMessage is not None:
                                                    message = replyMessage
                                                    is_reply = True
                                            except:
                                                pass
                                
                                if not is_external:
                                    message.to.clear()
                                message.to.add(email.get('email_to'))
                                message.sender.address = user.login
                                message.body = email.get('body')
                                # Sadly no alternative body for viewing impaired...
                                message.subject = mail.subject
                                message.cc.add(tools.email_split(mail.email_cc))
                                message.reply_to.add(user.login)
                                message.attachments.add(attachments)
                                if mail.parent_id and mail.subtype_id.name != 'Note':
                                    if mail.parent_id.o365ConversationID:
                                        mail.mail_message_id.o365ConversationID = mail.parent_id.o365ConversationID
                                        message.conversation_id = mail.parent_id.o365ConversationID
    
                                message.send()
                                if not mail.mail_message_id.o365ID and is_external:
                                    try:
                                        time.sleep(1)
                                        sent = list(mailbox.sent_folder().get_messages(limit=len(ids), batch=len(ids),
                                                                                       download_attachments=False))
                                        sent.sort(key=lambda element: element.sent, reverse=True)
                                        now = datetime.datetime.utcnow()
                                        for message in sent:
                                            if mail.subject == message.subject and abs(now - message.sent.utcnow()) < datetime.timedelta(seconds=2):
                                                mail.mail_message_id.o365ID = message.object_id
                                                mail.mail_message_id.o365ConversationID = message.conversation_id
                                                break
                                        time.sleep(1)
                                    except Exception as e:
                                        sentry_sdk.capture_exception(e)
    
                                if isinstance(process_pid, list):
                                    for pid in process_pid:
                                        process_pids.append(pid)
                                else:
                                    process_pids.append(process_pid)
                            # do not try to send via the normal way
                            mail.write({'state': 'sent', 'failure_reason': False})
                            _logger.info('Mail with ID %r successfully sent', mail.id)
                            mail._postprocess_sent_message(success_pids=process_pids)
                    except Exception as e:
                        sentry_sdk.capture_exception(e)
                        failure_reason = tools.ustr(e)
                        _logger.exception('failed sending mail (id: %s) due to %s', mail.id, failure_reason)
                        mail.write({'state': 'exception', 'failure_reason': failure_reason})
                        mail._postprocess_sent_message(failure_reason=failure_reason, failure_type='UNKNOWN')
                        if raise_exception:
                            if isinstance(e, (AssertionError, UnicodeEncodeError)):
                                if isinstance(e, UnicodeEncodeError):
                                    value = "Invalid text: %s" % e.object
                                else:
                                    # get the args of the original error, wrap into a value and throw a MailDeliveryException
                                    # that is an except_orm, with name and value as arguments
                                    value = '. '.join(e.args)
                                raise MailDeliveryException(("Mail Delivery Failed"), value)
                            raise
            else:
                super(linderaMail, mail).send(auto_commit=auto_commit, raise_exception=raise_exception)
