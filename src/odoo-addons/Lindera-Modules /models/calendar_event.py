import logging

from odoo import models, api, fields
from O365 import Account
from O365.calendar import Attendee, ResponseStatus, EventRecurrence
from O365.utils.utils import Recipient
from .odooTokenStore import odooTokenStore
from .ravenSingleton import ravenSingleton
import datetime
from dateutil.relativedelta import relativedelta
from openerp.osv import osv

_logger = logging.getLogger(__name__)

statusMap = {
	'tentative': 'tentativelyAccepted',
	'accepted': 'accepted',
	'declined': 'declined',
	'needsAction': 'notResponded'
}
indexMap = {
	'1': 'first',
	'2': 'second',
	'3': 'third',
	'4': 'fourth',
	'-1': 'last'
}

dayMap = {
	'MO': 'monday',
	'TU': 'tuesday',
	'WE': 'wednesday',
	'TH': 'thursday',
	'FR': 'friday',
	'SA': 'saturday',
	'SU': 'sunday',
}

WATCHKEYS = ['name', 'start', 'stop', 'privacy', 'allday', 'description', 'attendee_ids', 'location', 'rrule_type',
             'recurrency', 'interval', 'count', 'mo', 'tu', 'we', 'th', 'fr', 'sa', 'su', 'month_by', 'day', 'byday',
             'final_date', 'week_list']


class linderaEvent(models.Model):
	_inherit = 'calendar.event'

	o365ID = fields.Text('o365ID')

	@api.multi
	def detach_recurring_event(self, values=None):
		"""
		Detach an event from the recurring one. Creates an actual event from the virtual instance.
		:param values:
		:return:
		"""
		if not values:
			values = {}

		# get rid of the corresponding office Event Occurence
		# get office credentials if they exist
		CLIENT_ID = self.env['ir.config_parameter'].get_param('lindera.client_id')
		CLIENT_SECRET = self.env['ir.config_parameter'].get_param('lindera.client_secret')

		# sentry creds
		ravenClient = self.env['ir.config_parameter'].get_param('lindera.raven_client')
		ravenSingle = ravenSingleton(ravenClient)
		token_backend = odooTokenStore(self.env.user)
		if token_backend.check_token():
			try:
				account = Account((CLIENT_ID, CLIENT_SECRET), token=token_backend)
				if account.is_authenticated:
					calendar = account.schedule()
					self.__removeRecurrent(calendar, self.start, self.stop, self.name)
			except Exception as err:
				ravenSingle.Client.captureMessage(err)
				raise osv.except_osv('Error While Syncing!', str(err))

		# clear the office ID which would link back to the recurrring event otherwise.
		values['o365ID'] = ''

		# pass on to the super method
		return super(linderaEvent, self).detach_recurring_event(values)

	@api.model
	def create(self, values):
		"""
		Creates a new calendar_event instance and its office counterpart. Wraps existing method.
		:param values: initial values of the event
		:return: returns an event
		"""

		# get office credentials if they exist
		CLIENT_ID = self.env['ir.config_parameter'].get_param('lindera.client_id')
		CLIENT_SECRET = self.env['ir.config_parameter'].get_param('lindera.client_secret')

		# sentry creds
		ravenClient = self.env['ir.config_parameter'].get_param('lindera.raven_client')
		ravenSingle = ravenSingleton(ravenClient)

		# pass to the super method to get everything in place
		event = super(linderaEvent, self).create(values)

		# check credentials
		token_backend = odooTokenStore(self.env.user)
		if token_backend.check_token():
			try:
				# login
				account = Account((CLIENT_ID, CLIENT_SECRET), token=token_backend)
				if account.is_authenticated:
					# get calendar
					calendar = account.schedule()

					if event.o365ID and event.o365ID != '':
						# update
						officeEvent = calendar.get_default_calendar().get_event(event.o365ID)
						if not officeEvent:
							officeEvent = event.updateOffice(calendar)
							officeEvent.save()
					else:
						# new
						if event.active:
							# only create an office instance if it is also visible
							officeEvent = event.updateOffice(calendar)
							officeEvent.save()
							event.o365ID = officeEvent.object_id
			except Exception as err:
				ravenSingle.Client.captureMessage(err)
				raise osv.except_osv('Error While Syncing!', str(err))

		return event

	def updateOffice(self, calendar, event=None):
		"""
		Updates an office calendar entry from odoo data without saving it
		:param calendar: the calendar instance for which to create the entry
		:param event: the event to update. if None a new one will be created
		:return: returns the unsafed entry use .send() to send it
		"""

		created = False
		if event is None:
			created = True
			# get a new and empty office-event
			event = calendar.new_event()
			event.response_requested = False

		# fill it with the odoo values
		event.subject = self.name
		event.start = self.start
		event.end = self.stop
		event.privacy = self.privacy
		if self.location:
			event.location = {'displayName': self.location}
		event.is_all_day = self.allday
		if self.description:
			event.body = self.description
		attendees = list(map(lambda attendee: Attendee(attendee.email, response_status=ResponseStatus(event, {
			'response': statusMap[attendee.state] if not created and attendee.state != 'declined' else 'none'}),
		                                               event=event), self.attendee_ids))
		emails = list(map(lambda attendee: attendee.address, event.attendees))
		# filter out existing mails
		attendees = list(filter(lambda attendee: attendee.address not in emails, attendees))
		# filter out non user emails
		attendees = list(
			filter(lambda attendee: bool(self.env['res.users'].search([('email', '=', attendee.address)])), attendees))
		event.attendees.add(attendees)

		oldEnd = event.recurrence.end_date
		# clear recurrency (still some problems, when recurrency is getting disabled -.-)
		event.recurrence._clear_pattern()

		if self.recurrency:
			# fill recurrency
			event.recurrence.interval = self.interval
			if self.byday:
				event.recurrence.index = indexMap[self.byday]

			if self.rrule_type == 'weekly':
				event.recurrence.first_day_of_week = 'sunday'

			if self.rrule_type == 'monthly':
				event.recurrence.day_of_month = self.day

			if self.rrule_type == 'yearly':
				event.recurrence.day_of_month = self.day
				event.recurrence.month = self.start.month

			if not self.rrule_type == 'daily':
				event.recurrence.days_of_week = []
				if self.week_list and self.week_list != '':
					event.recurrence.days_of_week.append(dayMap[self.week_list])

				if self.mo:
					event.recurrence.days_of_week.append('monday')
				if self.tu:
					event.recurrence.days_of_week.append('tuesday')
				if self.we:
					event.recurrence.days_of_week.append('wednesday')
				if self.th:
					event.recurrence.days_of_week.append('thursday')
				if self.fr:
					event.recurrence.days_of_week.append('friday')
				if self.sa:
					event.recurrence.days_of_week.append('saturday')
				if self.su:
					event.recurrence.days_of_week.append('sunday')

			if not oldEnd == datetime.date.min:
				event.recurrence.end_date = self.final_date
				if self.end_type != 'end_date':
					finaldelta = relativedelta(days=((- 1) * (self.rrule_type == 'daily') - 1),
					                           weeks=((- 1) * (self.rrule_type == 'weekly')),
					                           months=((- 1) * (self.rrule_type == 'monthly')),
					                           years=((- 1) * (self.rrule_type == 'yearly')))
					event.recurrence.end_date = (self.final_date + finaldelta)  # .date()

			event.recurrence.start_date = self.start

		return event

	@api.multi
	def write(self, values):
		"""
		Is called whenever a field is changed (even during initialization!).
		:param values: changed fields
		:return: bool writeSuccess
		"""
		# get office credentials
		CLIENT_ID = self.env['ir.config_parameter'].get_param('lindera.client_id')
		CLIENT_SECRET = self.env['ir.config_parameter'].get_param('lindera.client_secret')

		# sentry creds
		ravenClient = self.env['ir.config_parameter'].get_param('lindera.raven_client')
		ravenSingle = ravenSingleton(ravenClient)

		# pass to super to get everything in place
		writeSuccess = super(linderaEvent, self).write(values)

		actualInstance = self

		# test if virtual
		if isinstance(self.id, str):
			# get the master to the virtual, since the virtuals don't get updated instantly -.-
			actualInstance = self.env['calendar.event'].with_context(virtual_id=False).search([('id', "=", self.id)])[0]

		# do we need to pass on to office?
		if len(list(filter(lambda key: key in WATCHKEYS, values.keys()))) > 0:
			# login
			token_backend = odooTokenStore(self.env.user)
			if token_backend.check_token():
				try:
					account = Account((CLIENT_ID, CLIENT_SECRET), token=token_backend)
					if account.is_authenticated:
						# get calendar
						calendar = account.schedule()
						if self.o365ID:
							# already has an ID so probably already exists
							event = calendar.get_default_calendar().get_event(self.o365ID)
							if not event:
								# create office Event if it somehow does not exist yet
								# (happens even before it gets to that point in create, so most office events are created here)
								officeEvent = actualInstance.updateOffice(calendar)
							else:
								# update office Event with data from here
								officeEvent = actualInstance.updateOffice(calendar, event)
							officeEvent.save()
						else:
							# completely new
							if self.active:
								officeEvent = actualInstance.updateOffice(calendar)
								officeEvent.save()
								self.o365ID = officeEvent.object_id
							pass
				except Exception as err:
					ravenSingle.Client.captureMessage(err)
					raise osv.except_osv('Error While Syncing!', str(err))
		return writeSuccess

	@api.multi
	def unlink(self, can_be_deleted=True):
		"""
		Removes an Event.
		:param can_be_deleted:
		:return:
		"""
		# office credentials
		CLIENT_ID = self.env['ir.config_parameter'].get_param('lindera.client_id')
		CLIENT_SECRET = self.env['ir.config_parameter'].get_param('lindera.client_secret')

		# sentry credentials
		ravenClient = self.env['ir.config_parameter'].get_param('lindera.raven_client')
		ravenSingle = ravenSingleton(ravenClient)

		if can_be_deleted:
			# only delete if it is actually fine
			# login
			token_backend = odooTokenStore(self.env.user)
			if token_backend.check_token():
				try:
					account = Account((CLIENT_ID, CLIENT_SECRET), token=token_backend)
					if account.is_authenticated:
						calendar = account.schedule()
						if self.o365ID:
							if '-' not in str(self.id):
								event = calendar.get_default_calendar().get_event(self.o365ID)
								if event:
									event.delete()
							else:
								# find the right one to remove
								self.__removeRecurrent(calendar, self.start, self.stop, self.name)
				except Exception as err:
					ravenSingle.Client.captureMessage(err)
					raise osv.except_osv('Error While Syncing!', str(err))

		return super(linderaEvent, self).unlink(can_be_deleted)

	@classmethod
	def __removeRecurrent(cls, calendar, start, stop, name):
		query = calendar.new_query('start').equals(start)
		query = query.chain('and').on_attribute(
			'end').equals(stop)
		query = query.chain('and').on_attribute('subject').equals(
			name)  # .chain('and').on_attribute('series_master_id').equals(self.o365ID)
		events = list(calendar.get_default_calendar().get_events(query=query))
		event = None
		# since start and stop don't count for nothing.... we need to check since recurring events could overlap...
		for tevent in events:
			if tevent.start.utctimetuple() == start.utctimetuple() and \
					(tevent.end.utctimetuple() == stop.utctimetuple() or
					 (tevent.end - datetime.timedelta(
						 seconds=1)).utctimetuple() == stop.utctimetuple()) and tevent.event_type.value != 'single_instance':
				event = tevent
				break
		if not event:
			for tevent in events:
				if tevent.event_type.value != 'single_instance':
					event = tevent
					break
		if event:
			event.delete()
