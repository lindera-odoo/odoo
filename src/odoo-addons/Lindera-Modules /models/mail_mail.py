import os
import logging
import re
import base64
from io import BytesIO

from odoo import models, fields, api
from O365 import Account
from .odooTokenStore import odooTokenStore
from odoo import tools
from odoo.addons.base.models.ir_mail_server import MailDeliveryException
from .ravenSingleton import ravenSingleton

_logger = logging.getLogger(__name__)


class linderaMail(models.Model):
	_inherit = 'mail.mail'

	@api.multi
	def send(self, auto_commit=False, raise_exception=False):
		CLIENT_ID = self.env['ir.config_parameter'].get_param('lindera.client_id')
		CLIENT_SECRET = self.env['ir.config_parameter'].get_param('lindera.client_secret')
		ravenClient = self.env['ir.config_parameter'].get_param('lindera.raven_client')
		ravenSingle = ravenSingleton(ravenClient)

		ids = self.ids

		for id in ids:
			mail = self.browse(id)
			token_backend = odooTokenStore(self.env.user)
			if token_backend.check_token():
				try:
					account = Account((CLIENT_ID, CLIENT_SECRET), token=token_backend)
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
						attachments = [(BytesIO(base64.b64decode(a['datas'])), a['datas_fname']) for a in attachments.sudo().read(['datas_fname', 'datas']) if a['datas'] is not False]

						mailbox = account.mailbox()

						# specific behavior to customize the send email for notified partners
						email_list = []
						if mail.email_to:
							values = mail._send_prepare_values()
							values['email_to'] = tools.email_split([mail.email_to])
							email_list.append(values)
						for partner in mail.recipient_ids:
							values = mail._send_prepare_values(partner=partner)
							values['partner_id'] = partner
							values['email_to'] = partner.email
							email_list.append(values)

						process_pids = []
						for email in email_list:
							process_pid = email.pop("partner_id", None)
							# set data
							message = mailbox.new_message()
							message.to.add(email.get('email_to'))
							message.sender.address = mail.author_id.email
							message.body = email.get('body')
							# Sadly no alternative body for viewing impaired...
							message.subject = mail.subject
							message.cc.add(tools.email_split(mail.email_cc))
							message.reply_to.add(tools.email_split(mail.reply_to))
							message.attachments.add(attachments)

							message.send()

							process_pids.append(process_pid)
						# do not try to send via the normal way
						mail.write({'state': 'sent', 'failure_reason': False})
						_logger.info('Mail with ID %r successfully sent', mail.id)
						mail._postprocess_sent_message(success_pids=process_pids)
				except Exception as e:
					ravenSingle.Client.captureMessage(e)
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


