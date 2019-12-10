import os
from odoo import models, fields, api
from openerp.osv import osv
from O365 import Account
from O365.address_book import Contact
from .odooTokenStore import odooTokenStore
from .ravenSingleton import ravenSingleton
import threading
import datetime

class linderaCalendarSyncer(models.Model):
	"""
    Mail sync addition to users
    """
	# _inherit = 'res.users'
	_name = 'lindera.office.contact'

	@api.model
	def syncCalendarScheduler(self):
		self.syncContacts()

	def syncCalendar(self):
		ravenClient = self.env['ir.config_parameter'].get_param(
			'lindera.raven_client')
		ravenSingle = ravenSingleton(ravenClient)
		CLIENT_ID = self.env['ir.config_parameter'].get_param('lindera.client_id')
		CLIENT_SECRET = self.env['ir.config_parameter'].get_param('lindera.client_secret')