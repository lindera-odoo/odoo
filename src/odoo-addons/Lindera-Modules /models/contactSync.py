import os
from odoo import models, fields, api
from openerp.osv import osv
from O365 import Account
from O365.address_book import Contact
from .odooTokenStore import odooTokenStore
from .ravenSingleton import ravenSingleton
import threading
import datetime


class linderaContactSyncer(models.Model):
	"""
    Mail sync addition to users
    """
	# _inherit = 'res.users'
	_name = 'lindera.office.contact'

	@api.model
	def syncContactsScheduler(self):
		self.syncContacts()

	def syncContacts(self):
		ravenClient = self.env['ir.config_parameter'].get_param(
			'lindera.raven_client')
		ravenSingle = ravenSingleton(ravenClient)
		CLIENT_ID = self.env['ir.config_parameter'].get_param('lindera.client_id')
		CLIENT_SECRET = self.env['ir.config_parameter'].get_param('lindera.client_secret')
		partners = self.env['res.partner'].search([])
		for syncUser in self.env['res.users'].search([]):
			token_backend = odooTokenStore(syncUser)
			if token_backend.check_token():
				try:
					account = Account((CLIENT_ID, CLIENT_SECRET), token=token_backend)
					if account.is_authenticated:
						address_book = account.address_book()
						contacts = list(address_book.get_contacts(10000, batch=1000))
						contacts = list(map(lambda elem: elem.main_email, contacts))
						for partner in partners:
							try:
								if partner.email not in contacts:
									contact = address_book.new_contact()
									if not partner.is_company:
										if partner.company_id:
											contact.company_name = partner.company_id.name
									contact.name = partner.name
									contact.display_name = partner.display_name
									contact.emails.add(partner.email)
									if partner.function:
										contact.job_title = partner.function
									if partner.title:
										contact.title = partner.title.name
									if partner.mobile:
										contact.mobile_phone = partner.mobile

									if partner.phone:
										contact.home_phones = partner.phone
									if partner.company_id:
										if partner.company_id.phone:
											contact.business_phones = partner.company_id.phone
									if partner.mobile:
										contact.mobile_phone = partner.mobile
									contact.categories = 'Odoo Imported'
									contact.save()
							except Exception as err:
								ravenSingle.Client.captureMessage(err)
								raise osv.except_osv('Error While Syncing!', str(err))
				except Exception as err:
					ravenSingle.Client.captureMessage(err)
					raise osv.except_osv('Error While Syncing!', str(err))
