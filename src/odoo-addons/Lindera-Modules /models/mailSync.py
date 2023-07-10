import os

import sentry_sdk

from odoo import models, fields, api
from odoo.osv import osv
from O365 import Account
from .odooTokenStore import odooTokenStore
from .sentrySingleton import sentrySingleton
import threading
import datetime

BATCH = 20


class linderaMailSyncer(models.Model):
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

	def forUser(self, syncUser, toCheck=-1):
		sentryClient = self.env['ir.config_parameter'].get_param(
			'lindera.raven_client')
		sentrySingle = sentrySingleton(sentryClient)
		CLIENT_ID = self.env['ir.config_parameter'].get_param('lindera.client_id')
		CLIENT_SECRET = self.env['ir.config_parameter'].get_param('lindera.client_secret')
		token_backend = odooTokenStore(syncUser)
		if token_backend.check_token():
			with sentry_sdk.push_scope() as scope:
				scope.set_extra('debug', False)
				try:
					account = Account((CLIENT_ID, CLIENT_SECRET), token_backend=token_backend)
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
							try:
								if message in inbox:
									# related partner might be weird without this...
									if message.sender.address != syncUser.email:
										contact = self.env['res.partner'].search(
											[('email', "=", message.sender.address)])
										if contact:
											user = self.env['res.users'].search([('partner_id', "=", contact[0].id),
																				 ('share', '=', False)])
											if not user:
												mail = self.env['mail.message'].search(
													[('o365ID', '=', message.object_id)])
												if not mail:
													mail = self.env['mail.message'].search(
														[('subject', '=', message.subject),
														 ('date', '=', message.sent),
														 ('email_from', '=',
														  contact[0].email)])
												if not mail:
													target_model = 'res.partner'
													target_id = contact[0].id
													parent_id = None
													prev_mail = self.env['mail.message'].search(
														[('o365ConversationID', '=', message.conversation_id)])
													if prev_mail:
														parent_id = prev_mail[0].id
														target_model = prev_mail[0].model
														target_id = prev_mail[0].res_id
														try:
															target_id = prev_mail[0].res_id.id
														except:
															pass
	
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
														'model': target_model,
														'res_id': target_id,
														'author_id': contact[0].id,
														'message_type': 'email',
														'o365ID': message.object_id,
														'o365ConversationID': message.conversation_id,
														'parent_id': parent_id
													})
													self.env.cr.commit()
								################################ SENT ##########################################################
								if message in sent:
									author = self.env['res.users'].search([('email', "=", message.sender.address),
																		   ('share', '=', False)])
									for recipient in message.to:
										# related partner might be weird without this...
										if recipient.address != syncUser.email:
											contact = self.env['res.partner'].search(
												[('email', "=", recipient.address)])
											if contact:
												user = self.env['res.users'].search(
													[('partner_id', "=", contact[0].id), ('share', '=', False)])
												if not user:
													# check if date
													mail = self.env['mail.message'].search(
														[('o365ID', '=', message.object_id)])
													if not mail:
														assert isinstance(message.sent,
														                  datetime.datetime), 'Must be a date!'
														self.env.cr.execute(
															"SELECT id FROM mail_message WHERE ABS(EXTRACT(EPOCH FROM (date::timestamp - '" + str(
																message.sent)[:-6] + "'::timestamp))) < 2")
														# self.env.cr.execute("SELECT id FROM mail_message ")
														results = self.env.cr.fetchall()
														if len(results) > 0:
															results = list(map(lambda res: res[0], results))
															mails = self.env['mail.message'].browse(results[0])
															mail = False
															for tmail in mails:
																if tmail.subject == message.subject:
																	if tmail.model == 'res.partner':
																		if tmail.res_id == contact[0].id:
																			mail = tmail
																			break
																	if tmail.model == 'crm.lead':
																		if tmail.needaction_partner_ids[0].id == \
																				contact[
																					0].id:
																			mail = tmail
																			break
	
													if not mail:
														target_model = 'res.partner'
														target_id = contact[0].id
														parent_id = None
														prev_mail = self.env['mail.message'].search(
															[('o365ConversationID', '=', message.conversation_id)])
														if prev_mail:
															parent_id = prev_mail[0].id
															target_model = prev_mail[0].model
															target_id = prev_mail[0].res_id
															try:
																target_id = prev_mail[0].res_id.id
															except:
																pass
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
																'model': target_model,
																'res_id': target_id,
																'author_id': author[0].commercial_partner_id.id,
																'message_type': 'email',
																'o365ID': message.object_id,
																'o365ConversationID': message.conversation_id,
																'parent_id': parent_id
															})
														else:
															self.env['mail.message'].create({
																'subject': message.subject,
																'date': message.sent,
																'body': message.body_preview,
																'email_from': message.sender.address,
																'attachment_ids': [[6, 0, attachments]],
																'model': target_model,
																'res_id': target_id,
																'message_type': 'email',
																'o365ID': message.object_id,
																'o365ConversationID': message.conversation_id,
																'parent_id': parent_id
															})
														self.env.cr.commit()
													else:
														if not mail[0].o365ID or mail[0].o365ConversationID:
															mail[0].o365ID = message.object_id
															mail[0].o365ConversationID = message.conversation_id
	
							except Exception as err:
								# error handler for single message
								sentry_sdk.capture_exception(err)
				except Exception as err:
					# error handling for authentication
					sentry_sdk.capture_exception(err)
					raise osv.except_osv('Error While Syncing!', str(err))

	def syncMails(self, toCheck=-1):
		for syncUser in self.env['res.users'].search([('share', '=', False)]):
			self.forUser(syncUser, toCheck)
