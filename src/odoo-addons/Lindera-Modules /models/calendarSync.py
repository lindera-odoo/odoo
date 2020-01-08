import os
from odoo import models, fields, api, exceptions
from openerp.osv import osv
from O365 import Account
from O365.calendar import Schedule
from O365.address_book import Contact
from .odooTokenStore import odooTokenStore
from .ravenSingleton import ravenSingleton
import threading
import datetime
from dateutil.relativedelta import relativedelta
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

indexMap = {
	'first': '1',
	'second': '2',
	'third': '3',
	'fourth': '4',
	'last': '-1'
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
		pass

	def handleNormalEvent(self, event):
		uid = self.env.user.id
		dbEvent = self.env['calendar.event'].search([('o365ID', "=", event.object_id)])
		privacy = event.sensitivity.value
		if privacy in privacyMap.keys():
			privacy = privacyMap[privacy]
		else:
			privacy = 'private'
		organizer = self.env['res.users'].search([('email', "=", event.organizer.address)])
		if organizer:
			uid = organizer[0].id
		if not dbEvent:
			dbEvent = self.env['calendar.event'].with_context(mail_create_nosubscribe=True).create({
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
				'description': event.body,
				'active': False,
				'o365ID': event.object_id
			}).with_context(no_mail_to_attendees=True)
			for attendee in event.attendees:
				partner = self.env['res.partner'].search([('email', "=", attendee.address)])
				attendeeDict = {
					'email': attendee.address,
					'event_id': dbEvent.id,
				}
				if attendee.response_status.status is not None:
					attendeeDict['state'] = statusMap[attendee.response_status.status.value]
				else:
					continue
				if partner:
					attendeeDict['partner_id'] = partner[0].id
					dbEvent.attendee_ids.create(attendeeDict)
					dbEvent.partner_ids += partner[0]
			if organizer:
				attendeeDict = {'email': organizer.email, 'event_id': dbEvent.id,
				                'state': 'accepted',
				                'partner_id': organizer[0].id}
				dbEvent.attendee_ids.create(attendeeDict)
				dbEvent.partner_ids += organizer[0].partner_id
		else:
			dbEvent.active = False
			dbEvent = dbEvent.with_context(no_mail_to_attendees=True)
			dbEvent.privacy = privacy
			dbEvent.location = event.location['displayName']
			dbEvent.allday = event.is_all_day
			dbEvent.body = event.body
			for attendee in event.attendees:
				dbAttendee = dbEvent.attendee_ids.search([('email', "=", attendee.address),
				                                          ('event_id', "=", dbEvent.id)])
				if dbAttendee and attendee.response_status.status is not None:
					dbAttendee.state = statusMap[attendee.response_status.status.value]
				else:
					partner = self.env['res.partner'].search([('email', "=", attendee.address)])
					eventID = dbEvent.id
					if isinstance(eventID, str):
						eventID = int(eventID.split('-')[0])
					attendeeDict = {
						'email': attendee.address,
						'event_id': eventID,
					}
					if attendee.response_status.status is not None:
						attendeeDict['state'] = statusMap[attendee.response_status.status.value]
					if partner:
						attendeeDict['partner_id'] = partner[0].id
						dbEvent.attendee_ids.create(attendeeDict)
						dbEvent.partner_ids += partner[0]
		dbEvent.active = True
		self.env.cr.commit()

	def handleRecurringEvent(self, event):
		uid = self.env.user.id
		# build the recurrence rule
		pattern = {'recurrency': True, 'final_date': str(event.recurrence.end_date), 'end_type': 'end_date',
		           'recurrent_id': 0}
		if event.recurrence.interval:
			pattern['rrule_type'] = 'daily'
			pattern['interval'] = event.recurrence.interval
			if event.recurrence.days_of_week:
				pattern['rrule_type'] = 'monthly'
				pattern['month_by'] = 'day'
				pattern['byday'] = indexMap[event.recurrence.index]
				if event.recurrence.first_day_of_week:
					for day in event.recurrence.days_of_week:
						pattern[day[:2]] = True
					# pattern['byday'] = ''
					# pattern['month_by'] = 'date'
					pattern['rrule_type'] = 'weekly'
				elif event.recurrence.month:
					pattern['rrule_type'] = 'yearly'

				if pattern['rrule_type'] != 'weekly':
					pattern['week_list'] = event.recurrence.days_of_week[0][:2].upper()

			elif event.recurrence.day_of_month:
				pattern['rrule_type'] = 'monthly'
				pattern['month_by'] = 'date'
				pattern['day'] = event.recurrence.day_of_month
				if event.recurrence.month:
					pattern['rrule_type'] = 'yearly'
		if pattern['final_date'] == str(datetime.date.min):
			pattern['final_date'] = datetime.date.today() + relativedelta(years=2)
		dbEvent = self.env['calendar.event'].with_context(virtual_id=False).search([('o365ID', "=", event.object_id)])
		privacy = event.sensitivity.value
		if privacy in privacyMap.keys():
			privacy = privacyMap[privacy]
		else:
			privacy = 'private'
		organizer = self.env['res.users'].search([('email', "=", event.organizer.address)])
		if organizer:
			uid = organizer[0].id
		if not dbEvent:
			createDir = {
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
				'description': event.body,
				'active': False,
				'o365ID': event.object_id
			}
			createDir.update(pattern)
			dbEvent = self.env['calendar.event'].with_context(mail_create_nosubscribe=True).create(createDir)
			dbEvent.write(pattern)
			dbEvent = dbEvent.with_context(no_mail_to_attendees=True)
			for attendee in event.attendees:
				partner = self.env['res.partner'].search([('email', "=", attendee.address)])
				attendeeDict = {
					'email': attendee.address,
					'event_id': dbEvent.id,
				}
				if attendee.response_status.status is not None:
					attendeeDict['state'] = statusMap[attendee.response_status.status.value]
				else:
					continue
				if partner:
					attendeeDict['partner_id'] = partner[0].id
					dbEvent.attendee_ids.create(attendeeDict)
					dbEvent.partner_ids += partner[0]
			if organizer:
				attendeeDict = {'email': organizer.email, 'event_id': dbEvent.id,
				                'state': 'accepted',
				                'partner_id': organizer[0].id}
				dbEvent.attendee_ids.create(attendeeDict)
				dbEvent.partner_ids += organizer[0].partner_id
		else:
			dbEvent.active = False
			dbEvent = dbEvent.with_context(no_mail_to_attendees=True)
			dbEvent.write(pattern)
			dbEvent.privacy = privacy
			dbEvent.location = event.location['displayName']
			dbEvent.allday = event.is_all_day
			dbEvent.body = event.body
			for attendee in event.attendees:
				dbAttendee = dbEvent.attendee_ids.search([('email', "=", attendee.address),
				                                          ('event_id', "=", dbEvent.id)])
				if dbAttendee and attendee.response_status.status is not None:
					dbAttendee.state = statusMap[attendee.response_status.status.value]
				else:
					partner = self.env['res.partner'].search([('email', "=", attendee.address)])
					eventID = dbEvent.id
					if isinstance(eventID, str):
						eventID = int(eventID.split('-')[0])
					attendeeDict = {
						'email': attendee.address,
						'event_id': eventID,
					}
					if attendee.response_status.status is not None:
						attendeeDict['state'] = statusMap[attendee.response_status.status.value]
					if partner:
						attendeeDict['partner_id'] = partner[0].id
						dbEvent.attendee_ids.create(attendeeDict)
						dbEvent.partner_ids += partner[0]
		dbEvent.active = True
		self.env.cr.commit()

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
						##################################NORMAL EVENTS#################################################
						events = list(calendar.get_events(1000, include_recurring=False))
						for event in events:
							try:
								if event.event_type.value == 'single_instance':
									self.handleNormalEvent(event)
									pass
							except exceptions.except_orm as err:
								print('Concurrent Update')
							except Exception as err:
								ravenSingle.Client.captureMessage(err)
								self.env.cr.rollback()
								raise osv.except_osv('Error While Syncing!', str(err))
						########################################RECURRENT EVENTS########################################
						start = datetime.datetime.utcnow()
						stop = start + datetime.timedelta(days=7)

						query = calendar.new_query('start').equals(start)
						query.chain('and').on_attribute('end').equals(stop)

						recevents = list(calendar.get_events(1000, include_recurring=True, query=query))
						for event in recevents:
							if event.event_type.value != 'single_instance':
								try:
									if event.event_type.value == 'exception':
										self.handleNormalEvent(event)
										pass
									else:
										master = calendar.get_default_calendar().get_event(event.series_master_id)
										self.handleRecurringEvent(master)
										pass
								except exceptions.except_orm as err:
									print('Concurrent Update')
								except Exception as err:
									ravenSingle.Client.captureMessage(err)
									self.env.cr.rollback()
									raise osv.except_osv('Error While Syncing!', str(err))
						pass
				except exceptions.except_orm as err:
					print('Concurrent Update')
				except Exception as err:
					ravenSingle.Client.captureMessage(err)
					raise osv.except_osv('Error While Syncing!', str(err))