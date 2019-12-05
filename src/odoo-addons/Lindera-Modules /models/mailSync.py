import os
from odoo import models, fields, api
from O365 import Account, FileSystemTokenBackend
import threading

BATCH = 20


class CustomUser(models.Model):
	"""
    Mail sync addition to users
    """
	# _inherit = 'res.users'
	_name = 'lindera.office.mail'

	@api.model
	def syncMailsScheduler(self):
		self.syncMails(BATCH)

	# @api.model
	def syncAllMailsScheduler(self):
		self.syncMails(100)

	def syncMails(self, toCheck=-1):
		CLIENT_ID = self.env['ir.config_parameter'].get_param('lindera.client_id')
		CLIENT_SECRET = self.env['ir.config_parameter'].get_param('lindera.client_secret')

		path = os.path.abspath(os.path.dirname(__file__) + '/../tokens')
		for file in os.listdir(path):
			if os.path.exists(path + '/' + file):
				token_backend = FileSystemTokenBackend(token_path=path, token_filename=file)
				account = Account((CLIENT_ID, CLIENT_SECRET), token=token_backend)
				if account.is_authenticated:
					mailbox = account.mailbox()
					inbox = list(mailbox.inbox_folder().get_messages(limit=toCheck, batch=BATCH, download_attachments=True))
					sent = list(mailbox.sent_folder().get_messages(limit=toCheck, batch=BATCH, download_attachments=True))

					messages = inbox + sent
					messages = sorted(messages, key=lambda elem: elem.sent)

					for message in messages:
						########################### INBOX ##############################################################
						if message in inbox:
							# related partner might be weird without this...
							if message.sender.address != file:
								contact = self.env['res.partner'].search([('email', "=", message.sender.address)])
								if contact:
									user = self.env['res.users'].search([('partner_id', "=", contact[0].id)])
									if not user:
										mail = self.env['mail.message'].search([('subject', '=', message.subject),
										                                        ('date', '=', message.sent),
										                                        ('email_from', '=', contact[0].email)])

										if not mail:
											attachments = []
											for attachment in message.attachments:
												attachment = self.env['ir.attachment'].create({
													'datas': attachment.content.encode(),
													'name': attachment.name,
													'datas_fname': attachment.name})
												self.env.cr.commit()
												attachments.append(attachment.id)
											self.env['mail.message'].create({
												'subject': message.subject,
												'date': message.sent,
												'body': message.body_preview,
												'email_from': contact[0].email,
												'attachment_ids': [[6, 0, attachments]],
												'model': 'res.partner',
												'res_id': contact[0].id,
												'author_id': contact[0].id
											})
											self.env.cr.commit()
						################################ SENT ##########################################################
						if message in sent:
							author = self.env['res.users'].search([('email', "=", message.sender.address)])
							for recipient in message.to:
								# related partner might be weird without this...
								if recipient.address != file:
									contact = self.env['res.partner'].search([('email', "=", recipient.address)])
									if contact:
										user = self.env['res.users'].search([('partner_id', "=", contact[0].id)])
										if not user:
											mail = self.env['mail.message'].search([('subject', '=', message.subject),
											                                        ('date', '=', message.sent),
											                                        ('res_id', '=', contact[0].id)])

											if not mail:
												attachments = []
												for attachment in message.attachments:
													attachment = self.env['ir.attachment'].create({
														'datas': attachment.content.encode(),
														'name': attachment.name,
														'datas_fname': attachment.name})
													self.env.cr.commit()
													attachments.append(attachment.id)
												if author:
													self.env['mail.message'].create({
														'subject': message.subject,
														'date': message.sent,
														'body': message.body_preview,
														'email_from': message.sender.address,
														'attachment_ids': [[6, 0, attachments]],
														'model': 'res.partner',
														'res_id': contact[0].id,
														'author_id': author[0].commercial_partner_id.id
													})
												else:
													self.env['mail.message'].create({
														'subject': message.subject,
														'date': message.sent,
														'body': message.body_preview,
														'email_from': message.sender.address,
														'attachment_ids': [[6, 0, attachments]],
														'model': 'res.partner',
														'res_id': contact[0].id
													})
												self.env.cr.commit()
				pass
