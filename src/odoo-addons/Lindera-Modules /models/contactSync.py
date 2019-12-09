import os
from odoo import models, fields, api
from openerp.osv import osv
from O365 import Account
from .odooTokenStore import odooTokenStore
from .ravenSingleton import ravenSingleton
import threading
import datetime

class CustomUser(models.Model):
	"""
    Mail sync addition to users
    """
	# _inherit = 'res.users'
	_name = 'lindera.office.contact'

	@api.model
	def syncMailsScheduler(self):
		self.syncContacts()

	# @api.model
	def syncAllMailsScheduler(self):
		self.syncContacts()

	def syncContacts(self):
		ravenClient = self.env['ir.config_parameter'].get_param(
			'lindera.raven_client')
		ravenSingle = ravenSingleton(ravenClient)
		CLIENT_ID = self.env['ir.config_parameter'].get_param('lindera.client_id')
		CLIENT_SECRET = self.env['ir.config_parameter'].get_param('lindera.client_secret')

		for syncUser in self.env['res.users'].search([]):
			token_backend = odooTokenStore(syncUser)
			if token_backend.check_token():
				try:
					account = Account((CLIENT_ID, CLIENT_SECRET), token=token_backend)
					if account.is_authenticated:
						mailbox = account.mailbox()
						inbox = list(
							mailbox.inbox_folder().get_messages(limit=toCheck, batch=BATCH, download_attachments=True))
						sent = list(
							mailbox.sent_folder().get_messages(limit=toCheck, batch=BATCH, download_attachments=True))

						messages = inbox + sent
						messages = sorted(messages, key=lambda elem: elem.sent)

						for message in messages:
							########################### INBOX ##############################################################
							if message in inbox:
								# related partner might be weird without this...
								if message.sender.address != syncUser.email:
									contact = self.env['res.partner'].search([('email', "=", message.sender.address)])
									if contact:
										user = self.env['res.users'].search([('partner_id', "=", contact[0].id)])
										if not user:
											mail = self.env['mail.message'].search([('subject', '=', message.subject),
											                                        ('date', '=', message.sent),
											                                        ('email_from', '=',
											                                         contact[0].email)])
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
													'author_id': contact[0].id,
													'message_type': 'email'
												})
												self.env.cr.commit()
							################################ SENT ##########################################################
							if message in sent:
								author = self.env['res.users'].search([('email', "=", message.sender.address)])
								for recipient in message.to:
									# related partner might be weird without this...
									if recipient.address != syncUser.email:
										contact = self.env['res.partner'].search([('email', "=", recipient.address)])
										if contact:
											user = self.env['res.users'].search([('partner_id', "=", contact[0].id)])
											if not user:
												# check if date
												assert isinstance(message.sent, datetime.datetime), 'Must be a date!'
												self.env.cr.execute(
													"SELECT id FROM mail_message WHERE ABS(EXTRACT(EPOCH FROM (date::timestamp - '" + str(
														message.sent)[:-6] + "'::timestamp))) < 2")
												self.env.cr.execute("SELECT id FROM mail_message ")
												results = self.env.cr.fetchall()
												mail = False
												for res in results:
													mail = self.env['mail.message'].search(
														[('subject', '=', message.subject),
														 ('id', '=', res[0]),
														 ('res_id', '=', contact[0].id)])
													if mail:
														break

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
															'author_id': author[0].commercial_partner_id.id,
															'message_type': 'email'
														})
													else:
														self.env['mail.message'].create({
															'subject': message.subject,
															'date': message.sent,
															'body': message.body_preview,
															'email_from': message.sender.address,
															'attachment_ids': [[6, 0, attachments]],
															'model': 'res.partner',
															'res_id': contact[0].id,
															'message_type': 'email'
														})
													self.env.cr.commit()
				except Exception as err:
					ravenSingle.Client.captureMessage(err)
					raise osv.except_osv('Error While Syncing!', str(err))
