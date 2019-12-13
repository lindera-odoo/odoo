import os
from odoo import models, fields, api
from openerp.osv import osv
from O365 import Account
from O365.address_book import Contact
from .odooTokenStore import odooTokenStore
from .ravenSingleton import ravenSingleton
import threading
import datetime
import pytz

privacyMap = {
	'normal': 'public',
	1: 'private',
	2: 'confidential'
}

statusMap = {
	'none': 'needsAction',
	'tentative': 'tentative',
	'declined': 'declined',
	'accepted': 'accepted',
	'organizer': 'accepted',
	'not_responded': 'needsAction',
	'tentatively_accepted': 'tentative',
}


class linderaCalendarSyncer(models.Model):
	"""
    Mail sync addition to users
    """
	# _inherit = 'res.users'
	_name = 'lindera.office.calendar'

	@api.model
	def syncCalendarScheduler(self):
		self.syncCalendar()

	def syncCalendar(self):
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
						calendar = account.schedule()
						events = list(calendar.get_events(1000, include_recurring=False))
						for event in events:
							try:
								uid = self.env.user.id
								dbEvent = self.env['calendar.event'].search([('name', "=", event.subject),
								                                             ('start', "=", event.start),
								                                             ('stop', "=", event.end)])
								privacy = event.sensitivity.value
								if privacy in privacyMap.keys():
									privacy = privacyMap[privacy]
								else:
									privacy = 'private'
								organizer = self.env['res.users'].search([('email', "=", event.organizer.address)])
								if organizer:
									uid = organizer[0].id
								if not dbEvent:
									dbEvent = self.env['calendar.event'].create({
										'name': event.subject,
										'start': str(event.start),
										'stop': str(event.end),
										'privacy': privacy,
										'location': event.location['displayName'],
										'allday': event.is_all_day,
										# 'show_as': event.show_as.value,
										'create_uid': uid,
										'write_uid': uid,
										'user_id': uid,
									})
									if event.subject == "test":
										test = 1
									for attendee in event.attendees:
										partner = self.env['res.partner'].search([('email', "=", attendee.address)])
										attendeeDict = {
											'email': attendee.address,
											'event_id': dbEvent.id,
											'state': statusMap[event.response_status.status.value]
										}
										if partner:
											attendeeDict['partner_id'] = partner[0].id
											dbAttendee = dbEvent.attendee_ids.create(attendeeDict)
											dbEvent.partner_ids += partner[0]
									if organizer:
										attendeeDict = {'email': organizer.email, 'event_id': dbEvent.id,
										                'state': 'accepted',
										                'partner_id': organizer[0].id}
										dbAttendee = dbEvent.attendee_ids.create(attendeeDict)
										dbEvent.partner_ids += organizer[0].partner_id
									self.env.cr.commit()
								pass
							except Exception as err:
								# ravenSingle.Client.captureMessage(err)
								self.env.cr.rollback()
								raise osv.except_osv('Error While Syncing!', str(err))
						pass
				except Exception as err:
					# ravenSingle.Client.captureMessage(err)
					raise osv.except_osv('Error While Syncing!', str(err))
