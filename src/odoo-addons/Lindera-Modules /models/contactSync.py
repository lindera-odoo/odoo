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
						partners = self.env['res.partner'].search([])
						address_book = account.address_book()
						for partner in partners:

							contact = address_book.new_contact()
				except Exception as err:
					ravenSingle.Client.captureMessage(err)
					raise osv.except_osv('Error While Syncing!', str(err))
