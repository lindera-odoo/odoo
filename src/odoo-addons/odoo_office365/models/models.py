# -*- coding: utf-8 -*-

import logging
import re

from odoo import fields, models, api, osv
from openerp.exceptions import ValidationError
from openerp.osv import osv
from openerp import _
import webbrowser
from odoo.http import request
from email.utils import formataddr

from odoo import _, api, fields, models, modules, SUPERUSER_ID, tools
from odoo.exceptions import UserError, AccessError
from odoo.osv import expression

import requests
import json
from datetime import datetime
import time
from dateutil import tz
from datetime import timedelta

_logger = logging.getLogger(__name__)
_image_dataurl = re.compile(r'(data:image/[a-z]+?);base64,([a-z0-9+/]{3,}=*)([\'"])', re.I)



class OfficeSettings(models.Model):
    """
    This class separates one time office 365 settings from Token generation settings
    """
    _name = "office.settings"


    field_name = fields.Char('Office365')
    redirect_url = fields.Char('Redirect URL')
    client_id = fields.Char('Client Id')
    secret = fields.Char('Secret')
    # login_url = fields.Char('Login URL', compute='_compute_url', readonly=True)

    @api.one
    def sync_data(self):
        try:
            if not self.client_id or not self.redirect_url or not self.secret:
                 raise osv.except_osv(_("Wrong Credentials!"), (_("Please Check your Credentials and try again")))
            else:
                self.env.user.redirect_url = self.redirect_url
                self.env.user.client_id = self.client_id
                self.env.user.secret = self.secret
                self.env.user.code = None
                self.env.user.token = None
                self.env.user.refresh_token = None
                self.env.user.expires_in = None
                self.env.user.office365_email = None
                self.env.user.office365_id_address = None

                self.env.cr.commit()

        except Exception as e:
            raise ValidationError(_(str(e)))
        raise osv.except_osv(_("Success!"), (_("Successfully Activated!")))


class Office365UserSettings(models.Model):
    """
    This class facilitates the users other than admin to enter office 365 credential
    """
    _name = 'office.usersettings'


    login_url = fields.Char('Login URL', compute='_compute_url', readonly=True)
    code = fields.Char('code')
    field_name = fields.Char('office')
    token = fields.Char('Office_Token')

    @api.one
    def _compute_url(self):


        settings = self.env['office.settings'].search([])
        settings = settings[0] if settings else settings
        if settings:
            self.login_url = 'https://login.microsoftonline.com/common/oauth2/v2.0/authorize?client_id=%s&redirect_uri=%s&response_type=code&scope=openid+offline_access+Calendars.ReadWrite+Mail.ReadWrite+Mail.Send+User.ReadWrite+Tasks.ReadWrite+Contacts.ReadWrite' % (
                settings.client_id, settings.redirect_url)

    @api.one
    def test_connectiom(self):

        try:

            settings = self.env['office.settings'].search([])
            settings = settings[0] if settings else settings

            if not settings.client_id or not settings.redirect_url or not settings.secret:
                raise osv.except_osv(_("Error!"), (_("Please ask admin to add Office365 settings!")))


            # pause.until(request.httprequest.referrer.find('code='))
            # time.sleep(40)
            # if not request.httprequest.referrer.find('code=') == -1:
                # self.code = request.httprequest.referrer.split('=')[1]


            header = {
                'Content-Type': 'application/x-www-form-urlencoded'
            }
            response = requests.post(
                'https://login.microsoftonline.com/common/oauth2/v2.0/token',
                data='grant_type=authorization_code&code=' + self.code + '&redirect_uri=' + settings.redirect_url + '&client_id=' + settings.client_id + '&client_secret=' + settings.secret
                , headers=header).content

            if 'error' in json.loads(response.decode('utf-8')) and json.loads(response.decode('utf-8'))['error']:
                raise UserError('Invalid Credentials . Please! Check your credential and  regenerate the code and try again!')

            else :
                response = json.loads((str(response)[2:])[:-1])
                self.env.user.token = response['access_token']
                self.env.user.refresh_token = response['refresh_token']
                self.token = response['refresh_token']


                self.env.user.expires_in = int(round(time.time() * 1000))
                self.env.user.code = self.code
                self.code = ""
                response = json.loads((requests.get(
                    'https://graph.microsoft.com/v1.0/me',
                    headers={
                        'Host': 'outlook.office.com',
                        'Authorization': 'Bearer {0}'.format(self.env.user.token),
                        'Accept': 'application/json',
                        'X-Target-URL': 'http://outlook.office.com',
                        'connection': 'keep-Alive'
                    }).content.decode('utf-8')))
                self.env.user.office365_email = response['userPrincipalName']
                self.env.user.office365_id_address = 'outlook_' + response['id'].upper() + '@outlook.com'
                self.env.cr.commit()
                print("code=",self.code)
                # print('token=', self.token)



        except Exception as e:
            raise ValidationError(_(str(e)))

        raise osv.except_osv(_("Success!"), (_("Token Generated!")))


class CustomUser(models.Model):
    """
    This class adds functionality to user for Office365 Integration
    """
    _inherit = 'res.users'


    login_url = fields.Char('Login URL', compute='_compute_url', readonly=True)
    code = fields.Char('code')
    token = fields.Char('Token', readonly=True)
    refresh_token = fields.Char('Refresh Token', readonly=True)
    expires_in = fields.Char('Expires IN', readonly=True)
    redirect_url = fields.Char('Redirect URL')
    client_id = fields.Char('Client Id')
    secret = fields.Char('Secret')
    office365_email = fields.Char('Office365 Email Address', readonly=True)
    office365_id_address = fields.Char('Office365 Id Address', readonly=True)
    send_mail_flag = fields.Boolean(string='Send messages using office365 Mail', default=True)
    is_task_sync_on = fields.Boolean('is sync in progress', default=False)

    @api.one
    def _compute_url(self):
        """
        this function creates a url. By hitting this URL creates a code that is require to generate token. That token will be sent with every API request

        :return:
        """
        self.login_url = 'https://login.microsoftonline.com/common/oauth2/v2.0/authorize?client_id=%s&redirect_uri=%s&response_type=code&scope=openid+offline_access+Calendars.ReadWrite+Mail.ReadWrite+Mail.Send+User.ReadWrite+Tasks.ReadWrite+Contacts.ReadWrite' % (
            self.client_id, self.redirect_url)

    @api.one
    def user_login(self):
        """
        This function generates token using code generated using above login URL
        :return:
        """
        try:
            web = webbrowser.open(self.login_url)


        except Exception as e:
            raise ValidationError(_(str(e)))

        # raise osv.except_osv(_("Success!"), (_("Token Generated!")))

    def auto_import_calendar(self):
        print("###########################",self.env.user.name)
        self.import_calendar()

    @api.model
    def auto_export_calendar(self):
        print("###########################", self.env.user.name)
        self.export_calendar()

    # @api.one
    def import_calendar(self):
        """
        this function imports Office 365  Calendar to Odoo Calendar

        :return:
        """

        if self.env.user.token:
            try:
                if self.env.user.expires_in:
                    expires_in = datetime.fromtimestamp(int(self.env.user.expires_in) / 1e3)
                    expires_in = expires_in + timedelta(seconds=3600)
                    nowDateTime = datetime.now()
                    if nowDateTime > expires_in:
                        self.generate_refresh_token()

                response = requests.get(
                    'https://graph.microsoft.com/v1.0/me/events',
                    headers={
                        'Host': 'outlook.office.com',
                        'Authorization': 'Bearer {0}'.format(self.env.user.token),
                        'Accept': 'application/json',
                        'X-Target-URL': 'http://outlook.office.com',
                        'connection': 'keep-Alive'
                    }).content
                if 'value' not in json.loads((response.decode('utf-8'))).keys():
                    raise osv.except_osv(response)
                events = json.loads((response.decode('utf-8')))['value']
                for event in events:

                    # if 'showAs' in event:
                    odoo_meeting = self.env['calendar.event'].search([("office_id", "=", event['id'])])
                    if odoo_meeting:
                        odoo_meeting.unlink()
                        self.env.cr.commit()

                    odoo_event = self.env['calendar.event'].create({
                        'office_id': event['id'],
                        'name': event['subject'],
                        "description": event['bodyPreview'],
                        'location': (event['location']['address']['city'] + ', ' + event['location']['address'][
                            'countryOrRegion']) if 'address' in event['location'] and 'city' in event['location'][
                            'address'].keys() else "",
                        'start':datetime.strptime(event['start']['dateTime'][:-8], '%Y-%m-%dT%H:%M:%S'),
                        'stop': datetime.strptime(event['end']['dateTime'][:-8], '%Y-%m-%dT%H:%M:%S'),
                        'allday': event['isAllDay'],
                        'show_as': event['showAs'] if 'showAs' in event and (event['showAs'] == 'free' or event['showAs'] == 'busy') else None,
                        'recurrency': True if event['recurrence'] else False,
                        'end_type': 'end_date' if event['recurrence'] else "",
                        'rrule_type': event['recurrence']['pattern']['type'].replace('absolute', '').lower() if
                        event[
                            'recurrence'] else "",
                        'count': event['recurrence']['range']['numberOfOccurrences'] if event['recurrence'] else "",
                        'final_date': datetime.strptime(event['recurrence']['range']['endDate'],
                                                        '%Y-%m-%d').strftime(
                            '%Y-%m-%d') if event['recurrence'] else None,
                        'mo': True if event['recurrence'] and 'daysOfWeek' in event['recurrence'][
                            'pattern'].keys() and 'monday' in event['recurrence']['pattern'][
                                          'daysOfWeek'] else False,
                        'tu': True if event['recurrence'] and 'daysOfWeek' in event['recurrence'][
                            'pattern'].keys() and 'tuesday' in event['recurrence']['pattern'][
                                          'daysOfWeek'] else False,
                        'we': True if event['recurrence'] and 'daysOfWeek' in event['recurrence'][
                            'pattern'].keys() and 'wednesday' in event['recurrence']['pattern'][
                                          'daysOfWeek'] else False,
                        'th': True if event['recurrence'] and 'daysOfWeek' in event['recurrence'][
                            'pattern'].keys() and 'thursday' in event['recurrence']['pattern'][
                                          'daysOfWeek'] else False,
                        'fr': True if event['recurrence'] and 'daysOfWeek' in event['recurrence'][
                            'pattern'].keys() and 'friday' in event['recurrence']['pattern'][
                                          'daysOfWeek'] else False,
                        'sa': True if event['recurrence'] and 'daysOfWeek' in event['recurrence'][
                            'pattern'].keys() and 'saturday' in event['recurrence']['pattern'][
                                          'daysOfWeek'] else False,
                        'su': True if event['recurrence'] and 'daysOfWeek' in event['recurrence'][
                            'pattern'].keys() and 'sunday' in event['recurrence']['pattern'][
                                          'daysOfWeek'] else False,
                    })
                    partner_ids = []
                    attendee_ids = []
                    for attendee in event['attendees']:
                        partner = self.env['res.partner'].search(
                            [('email', "=", attendee['emailAddress']['address'])])
                        if not partner:
                            partner = self.env['res.partner'].create({
                                'name': attendee['emailAddress']['name'],
                                'email': attendee['emailAddress']['address'],
                            })
                        partner_ids.append(partner[0].id)
                        odoo_attendee = self.env['calendar.attendee'].create({
                            'partner_id': partner[0].id,
                            'event_id': odoo_event.id,
                            'email': attendee['emailAddress']['address'],
                            'common_name': attendee['emailAddress']['name'],

                        })
                        attendee_ids.append(odoo_attendee.id)
                    if not event['attendees']:
                        odoo_attendee = self.env['calendar.attendee'].create({
                            'partner_id': self.env.user.partner_id.id,
                            'event_id': odoo_event.id,
                            'email': self.env.user.partner_id.email,
                            'common_name': self.env.user.partner_id.name,

                        })
                        attendee_ids.append(odoo_attendee.id)
                        partner_ids.append(self.env.user.partner_id.id)
                    odoo_event.write({
                        'attendee_ids': [[6, 0, attendee_ids]],
                        'partner_ids': [[6, 0, partner_ids]]
                    })
                    self.env.cr.commit()
                else:
                    print('sorryy event is tentative')
                    print(event['showAs'])
                    print((event['subject']))


                    # else:
                    #     raise osv.except_osv((event['subject']),_(event['ShowAs']))




            except Exception as e:
                print(e)

        else:
            raise osv.except_osv(_("Token is missing!"), (_(" Token is not founded! ")))

    # @api.one
    def export_calendar(self):
        """
        this function export  odoo calendar event  to office 365 Calendar

        """
        if self.env.user.token:
            try:
                if self.env.user.expires_in:
                    expires_in = datetime.fromtimestamp(int(self.env.user.expires_in) / 1e3)
                    expires_in = expires_in + timedelta(seconds=3600)
                    nowDateTime = datetime.now()
                    if nowDateTime > expires_in:
                        self.generate_refresh_token()

                header = {
                    'Authorization': 'Bearer {0}'.format(self.env.user.token),
                    'Content-Type': 'application/json'
                }
                response = requests.get(
                    'https://graph.microsoft.com/v1.0/me/calendars',
                    headers={
                        'Host': 'outlook.office.com',
                        'Authorization': 'Bearer {0}'.format(self.env.user.token),
                        'Accept': 'application/json',
                        'X-Target-URL': 'http://outlook.office.com',
                        'connection': 'keep-Alive'
                    }).content
                if 'value' not in json.loads((response.decode('utf-8'))).keys():
                    raise osv.except_osv(("Access Token Expired!"), (" Please Regenerate Access Token !"))
                calendars = json.loads((response.decode('utf-8')))['value']
                calendar_id = calendars[0]['id']

                meetings = self.env['calendar.event'].search([("office_id", "=", False),("create_uid", '=', self.env.user.id)])
                added_meetings = self.env['calendar.event'].search([("office_id", "!=", False),("create_uid", '=', self.env.user.id)])

                added = []
                for meeting in meetings:
                    temp = meeting
                    id = str(meeting.id).split('-')[0]
                    metngs = [meeting for meeting in meetings if id in str(meeting.id)]
                    index = len(metngs)
                    meeting = metngs[index - 1]
                    if meeting.start is not None:
                        metting_start = meeting.start.strftime(
                            '%Y-%m-%d T %H:%M:%S') if meeting.start else meeting.start
                    else:
                        metting_start = None

                    payload = {
                        "subject": meeting.name,
                        "attendees": self.getAttendee(meeting.attendee_ids),
                        'reminderMinutesBeforeStart': self.getTime(meeting.alarm_ids),
                        "start": {
                            "dateTime": meeting.start.strftime(
                                '%Y-%m-%d T %H:%M:%S') if meeting.start else meeting.start,
                            "timeZone": "UTC"
                        },
                        "end": {
                            "dateTime": meeting.stop.strftime('%Y-%m-%d T %H:%M:%S') if meeting.stop else meeting.stop,
                            "timeZone": "UTC"
                        },
                        "showAs": meeting.show_as,
                        "location": {
                            "displayName": meeting.location if meeting.location else "",
                        },

                    }
                    if meeting.recurrency:
                        payload.update({"recurrence": {
                            "pattern": {
                                "daysOfWeek": self.getdays(meeting),
                                "type": (
                                            'Absolute' if meeting.rrule_type != "weekly" and meeting.rrule_type != "daily" else "") + meeting.rrule_type,
                                "interval": meeting.interval,
                                "month": int(meeting.start.month),  # meeting.start[5] + meeting.start[6]),
                                "dayOfMonth": int(meeting.start.day),  # meeting.start[8] + meeting.start[9]),
                                "firstDayOfWeek": "sunday",
                                # "index": "first"
                            },
                            "range": {
                                "type": "endDate",
                                "startDate": str(
                                    str(meeting.start.year) + "-" + str(meeting.start.month) + "-" + str(meeting.start.day)),
                                "endDate": str(meeting.final_date),
                                "recurrenceTimeZone": "UTC",
                                "numberOfOccurrences": meeting.count,
                            }
                        }})
                    if meeting.name not in added:
                        response = requests.post(
                            'https://graph.microsoft.com/v1.0/me/calendars/' + calendar_id + '/events',
                            headers=header, data=json.dumps(payload)).content
                        if 'id' in json.loads((response.decode('utf-8'))):
                            temp.write({
                                'office_id': json.loads((response.decode('utf-8')))['id']
                            })
                            self.env.cr.commit()
                            if meeting.recurrency:
                                added.append(meeting.name)






            except Exception as e:
                raise ValidationError(_(str(e)))


        # raise osv.except_osv(_("Success!"), (_(" Sync Successfully !")))

    def getAttendee(self, attendees):
        """
        Get attendees from odoo and convert to attendees Office365 accepting
        :param attendees:
        :return: Office365 accepting attendees

        """
        attendee_list = []
        for attendee in attendees:
            attendee_list.append({
                "status": {
                    "response": 'Accepted',
                    "time": datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ')
                },
                "type": "required",
                "emailAddress": {
                    "address": attendee.email,
                    "name": attendee.display_name
                }
            })
        return attendee_list

    def getTime(self, alarm):
        """
        Convert ODOO time to minutes as Office365 accepts time in minutes
        :param alarm:
        :return: time in minutes
        """
        if alarm.interval == 'minutes':
            return alarm[0].duration
        elif alarm.interval == "hours":
            return alarm[0].duration * 60
        elif alarm.interval == "days":
            return alarm[0].duration * 60 * 24

    def getdays(self, meeting):
        """
        Returns days of week the event will occure
        :param meeting:
        :return: list of days
        """
        days = []
        if meeting.su:
            days.append("sunday")
        if meeting.mo:
            days.append("monday")
        if meeting.tu:
            days.append("tuesday")
        if meeting.we:
            days.append("wednesday")
        if meeting.th:
            days.append("thursday")
        if meeting.fr:
            days.append("friday")
        if meeting.sa:
            days.append("saturday")
        return days




    def getAttachment(self, message):
        if self.env.user.expires_in:
            expires_in = datetime.fromtimestamp(int(self.env.user.expires_in) / 1e3)
            expires_in = expires_in + timedelta(seconds=3600)
            nowDateTime = datetime.now()
            if nowDateTime > expires_in:
                self.generate_refresh_token()

        response = requests.get(
            'https://graph.microsoft.com/v1.0/me/messages/' + message['id'] + '/attachments/',
            headers={
                'Host': 'outlook.office.com',
                'Authorization': 'Bearer {0}'.format(self.env.user.token),
                'Accept': 'application/json',
                'X-Target-URL': 'http://outlook.office.com',
                'connection': 'keep-Alive'
            }).content
        attachments = json.loads((response.decode('utf-8')))['value']
        attachment_ids = []
        for attachment in attachments:
            if 'contentBytes' not in attachment or 'name' not in attachment:
                continue
            odoo_attachment = self.env['ir.attachment'].create({
                'datas': attachment['contentBytes'],
                'name': attachment["name"],
                'datas_fname': attachment["name"]})
            self.env.cr.commit()
            attachment_ids.append(odoo_attachment.id)
        return attachment_ids

    @api.model
    def auto_import_tasks(self):
        print("###########################", self.env.user.name)
        self.import_tasks()

    @api.model
    def auto_export_tasks(self):
        print("###########################", self.env.user.name)
        self.export_tasks()

    def import_tasks(self):

        """
        import tast from office 365 to odoo

        :return: None
        """
        if self.env.user.token:
            try:
                if self.env.user.expires_in:
                    expires_in = datetime.fromtimestamp(int(self.env.user.expires_in) / 1e3)
                    expires_in = expires_in + timedelta(seconds=3600)
                    nowDateTime = datetime.now()
                    if nowDateTime > expires_in:
                        self.generate_refresh_token()

                response = requests.get(
                    'https://graph.microsoft.com/beta/me/outlook/tasks',
                    headers={
                        'Host': 'outlook.office.com',
                        'Authorization': 'Bearer {0}'.format(self.env.user.token),
                        'Content-type': 'application/json',
                        'X-Target-URL': 'http://outlook.office.com',
                        'connection': 'keep-Alive'
                    }).content
                if 'value' not in json.loads((response.decode('utf-8'))).keys():
                    raise osv.except_osv(response)
                tasks = json.loads((response.decode('utf-8')))['value']
                partner_model = self.env['ir.model'].search([('model', '=', 'res.partner')])
                partner = self.env['res.partner'].search([('email', '=', self.env.user.email)])
                activity_type = self.env['mail.activity.type'].search([('name', '=', 'Todo')])
                if partner_model:
                    self.env.user.is_task_sync_on = True
                    self.env.cr.commit()
                    for task in tasks:
                        if not self.env['mail.activity'].search([('office_id', '=', task['id'])]) and task[
                            'status'] != 'completed':
                            if 'dueDateTime' in task:
                                if task['dueDateTime'] is None:
                                    continue
                            else:
                                continue

                            self.env['mail.activity'].create({
                                'res_id': partner[0].id,
                                'activity_type_id': activity_type.id,
                                'summary': task['subject'],
                                'date_deadline': (
                                    datetime.strptime(task['dueDateTime']['dateTime'][:-16], '%Y-%m-%dT')).strftime(
                                    '%Y-%m-%d'),
                                'note': task['body']['content'],
                                'res_model_id': partner_model.id,
                                'office_id': task['id'],
                            })
                        elif self.env['mail.activity'].search([('office_id', '=', task['id'])]) and task[
                            'status'] != 'completed':
                            activity = self.env['mail.activity'].search([('office_id', '=', task['id'])])[0]
                            activity.write({
                                'res_id': partner[0].id,
                                'activity_type_id': activity_type.id,
                                'summary': task['subject'],
                                'date_deadline': (
                                    datetime.strptime(task['dueDateTime']['dateTime'][:-16], '%Y-%m-%dT')).strftime(
                                    '%Y-%m-%d'),
                                'note': task['body']['content'],
                                'res_model_id': partner_model.id,
                                'office_id': task['id'],
                            })
                        elif self.env['mail.activity'].search([('office_id', '=', task['id'])]) and task[
                            'status'] == 'completed':
                            activity = self.env['mail.activity'].search([('office_id', '=', task['id'])])[0]
                            activity.unlink()

                        self.env.cr.commit()

                odoo_activities = self.env['mail.activity'].search(
                    [('office_id', '!=', None), ('res_id', '=', self.env.user.partner_id.id)])
                task_ids = [task['id'] for task in tasks]
                for odoo_activity in odoo_activities:
                    if odoo_activity.office_id not in task_ids:
                        odoo_activity.unlink()
                        self.env.cr.commit()
                self.env.user.is_task_sync_on = False
                self.env.cr.commit()

            except Exception as e:
                self.env.user.is_task_sync_on = False
                self.env.cr.commit()
                raise ValidationError(_(str(e)))
            # raise osv.except_osv(_("Success!"), (_(" Tasks are  Successfully Imported !")))

        else:
            raise osv.except_osv(('Token is missing!'),_('Please ! Generate Token and try Again'))


    def export_tasks(self):
        if self.env.user.token:
            if self.env.user.expires_in:
                expires_in = datetime.fromtimestamp(int(self.env.user.expires_in) / 1e3)
                expires_in = expires_in + timedelta(seconds=3600)
                nowDateTime = datetime.now()
                if nowDateTime > expires_in:
                    self.generate_refresh_token()

            odoo_activities = self.env['mail.activity'].search([('res_id', '=', self.env.user.partner_id.id)])
            for activity in odoo_activities:
                url = 'https://graph.microsoft.com/beta/me/outlook/tasks'
                if activity.office_id:
                    url += '/' + activity.office_id

                data = {
                    'subject': activity.summary if activity.summary else activity.note,
                    "body": {
                        "contentType": "html",
                        "content": activity.note
                    },
                    "dueDateTime": {
                        "dateTime": str(activity.date_deadline) + 'T00:00:00Z',
                        "timeZone": "UTC"
                    },
                }
                if activity.office_id:

                    response = requests.patch(
                        url, data=json.dumps(data),
                        headers={
                            'Host': 'outlook.office.com',
                            'Authorization': 'Bearer {0}'.format(self.env.user.env.user.token),
                            'Accept': 'application/json',
                            'Content-Type': 'application/json',
                            'X-Target-URL': 'http://outlook.office.com',
                            'connection': 'keep-Alive'
                        }).content
                else:
                    response = requests.post(
                        url, data=json.dumps(data),
                        headers={

                            'Host': 'outlook.office.com',
                            'Authorization': 'Bearer {0}'.format(self.env.user.token),
                            'Accept': 'application/json',
                            'Content-Type': 'application/json',
                            'X-Target-URL': 'http://outlook.office.com',
                            'connection': 'keep-Alive'
                        }).content

                    if 'id' not in json.loads((response.decode('utf-8'))).keys():
                        raise osv.except_osv(_("Error!"), (_(response["error"])))
                    activity.office_id = json.loads((response.decode('utf-8')))['id']
                self.env.cr.commit()

                # raise osv.except_osv(_("Success!"), (_("Tasks are Successfully exported! !")))


    def developer_test(self):
        try:
            channel = self.env['mail.channel'].search()
            raise osv.except_osv(_("Error!"), (_(channel)))
        except Exception as e:
            # self.env.user.send_mail_flag = True
            self.env.cr.commit()
            raise ValidationError(_(str(e)))
        self.env.cr.commit()

    @api.model
    def sync_customer_mail_scheduler(self):
        print("###########################", self.env.user.name)
        self.sync_customer_mail()

    def sync_customer_mail(self):
        try:
            self.env.cr.commit()
            self.sync_customer_inbox_mail()
            self.sync_customer_sent_mail()

        except Exception as e:
            self.env.cr.commit()
            raise ValidationError(_(str(e)))
        self.env.cr.commit()

    def sync_customer_inbox_mail(self):
        if self.env.user.token:
            try:
                if self.env.user.expires_in:
                    expires_in = datetime.fromtimestamp(int(self.env.user.expires_in) / 1e3)
                    expires_in = expires_in + timedelta(seconds=3600)
                    nowDateTime = datetime.now()
                    if nowDateTime > expires_in:
                        self.generate_refresh_token()

                response = requests.get(
                    'https://graph.microsoft.com/v1.0/me/mailFolders',
                    headers={
                        'Host': 'outlook.office.com',
                        'Authorization': 'Bearer {0}'.format(self.env.user.token),
                        'Accept': 'application/json',
                        'X-Target-URL': 'http://outlook.office.com',
                        'connection': 'keep-Alive'
                    }).content
                if 'value' not in json.loads((response.decode('utf-8'))).keys():
                    raise osv.except_osv("Access TOken Expired!", " Please Regenerate Access Token !")
                folders = json.loads((response.decode('utf-8')))['value']
                inbox_id = [folder['id'] for folder in folders if folder['displayName'] == 'Inbox']
                if inbox_id:
                    inbox_id = inbox_id[0]
                    response = requests.get(
                        'https://graph.microsoft.com/v1.0/me/mailFolders/' + inbox_id + '/messages?$top=100&$count=true',
                        headers={
                            'Host': 'outlook.office.com',
                            'Authorization': 'Bearer {0}'.format(self.env.user.token),
                            'Accept': 'application/json',
                            'X-Target-URL': 'http://outlook.office.com',
                            'connection': 'keep-Alive'
                        }).content
                    if 'value' not in json.loads((response.decode('utf-8'))).keys():
                        raise osv.except_osv("Access TOken Expired!", " Please Regenerate Access Token !")

                    else:
                        messages = json.loads((response.decode('utf-8')))['value']
                        for message in messages:
                            if 'from' not in message.keys() or self.env['mail.mail'].search(
                                    [('office_id', '=', message['conversationId'])]) or self.env['mail.message'].search(
                                [('office_id', '=', message['conversationId'])]):
                                continue

                            if 'address' not in message.get('from').get('emailAddress') or message['bodyPreview'] == "":
                                continue

                            attachment_ids = self.getAttachment(message)

                            from_partner = self.env['res.partner'].search(
                                [('email', "=", message['from']['emailAddress']['address'])])
                            if not from_partner:
                                continue
                            from_partner = from_partner[0] if from_partner else from_partner
                            # if from_partner:
                            #     from_partner = from_partner[0]
                            recipient_partners = []
                            channel_ids = []
                            for recipient in message['toRecipients']:
                                if recipient['emailAddress'][
                                    'address'].lower() == self.env.user.office365_email.lower() or \
                                        recipient['emailAddress'][
                                            'address'].lower() == self.env.user.office365_id_address.lower():
                                    to_user = self.env['res.users'].search(
                                        [('id', "=", self._uid)])
                                else:
                                    to = recipient['emailAddress']['address']
                                    to_user = self.env['res.users'].search(
                                        [('office365_id_address', "=", to)])
                                    to_user = to_user[0] if to_user else to_user

                                if to_user:
                                    to_partner = to_user.partner_id
                                    recipient_partners.append(to_partner.id)
                            date = datetime.strptime(message['sentDateTime'], "%Y-%m-%dT%H:%M:%SZ")
                            self.env['mail.message'].create({
                                'subject': message['subject'],
                                'date': date,
                                'body': message['bodyPreview'],
                                'email_from': message['from']['emailAddress']['address'],
                                'partner_ids': [[6, 0, recipient_partners]],
                                'attachment_ids': [[6, 0, attachment_ids]],
                                'office_id': message['conversationId'],
                                'author_id': from_partner.id,
                                'model': 'res.partner',
                                'res_id': from_partner.id
                            })
                            self.env.cr.commit()
            except Exception as e:
                # self.env.user.send_mail_flag = True
                raise ValidationError(_(str(e)))

    def sync_customer_sent_mail(self):
        """
        :return:
        """
        if self.env.user.token:
            try:
                if self.env.user.expires_in:
                    expires_in = datetime.fromtimestamp(int(self.env.user.expires_in) / 1e3)
                    expires_in = expires_in + timedelta(seconds=3600)
                    nowDateTime = datetime.now()
                    if nowDateTime > expires_in:
                        self.generate_refresh_token()

                response = requests.get(
                    'https://graph.microsoft.com/v1.0/me/mailFolders',
                    headers={
                        'Host': 'outlook.office.com',
                        'Authorization': 'Bearer {0}'.format(self.env.user.token),
                        'Accept': 'application/json',
                        'X-Target-URL': 'http://outlook.office.com',
                        'connection': 'keep-Alive'
                    }).content
                if 'value' not in json.loads((response.decode('utf-8'))).keys():
                    raise osv.except_osv("Access Token Expired!", " Please Regenerate Access Token !")
                else:
                    folders = json.loads((response.decode('utf-8')))['value']
                    sentbox_folder_id = [folder['id'] for folder in folders if folder['displayName'] == 'Sent Items']
                    if sentbox_folder_id:
                        sentbox_id = sentbox_folder_id[0]
                        response = requests.get(
                            'https://graph.microsoft.com/v1.0/me/mailFolders/' + sentbox_id + '/messages?$top=100000&$count=true',
                            headers={
                                'Host': 'outlook.office.com',
                                'Authorization': 'Bearer {0}'.format(self.env.user.token),
                                'Accept': 'application/json',
                                'X-Target-URL': 'http://outlook.office.com',
                                'connection': 'keep-Alive'
                            }).content
                        if 'value' not in json.loads((response.decode('utf-8'))).keys():

                            raise osv.except_osv("Access Token Expired!", " Please Regenerate Access Token !")
                        else:
                            messages = json.loads((response.decode('utf-8')))['value']
                            for message in messages:
                                print(message['bodyPreview'])

                                if 'from' not in message.keys() or self.env['mail.mail'].search(
                                        [('office_id', '=', message['conversationId'])]) or self.env[
                                    'mail.message'].search(
                                    [('office_id', '=', message['conversationId'])]):
                                    continue

                                if message['bodyPreview'] == "":
                                    continue

                                attachment_ids = self.getAttachment(message)
                                if message['from']['emailAddress'][
                                    'address'].lower() == self.env.user.office365_email.lower() or \
                                        message['from']['emailAddress'][
                                            'address'].lower() == self.env.user.office365_id_address.lower():
                                    email_from = self.env.user.email
                                else:
                                    email_from = message['from']['emailAddress']['address']

                                from_user = self.env['res.users'].search(
                                    [('id', "=", self._uid)])
                                if from_user:
                                    from_partner = from_user.partner_id
                                else:
                                    continue

                                channel_ids = []
                                for recipient in message['toRecipients']:

                                    to_partner = self.env['res.partner'].search(
                                        [('email', "=", recipient['emailAddress']['address'])])
                                    to_partner = to_partner[0] if to_partner else to_partner

                                    if not to_partner:
                                        continue
                                    date = datetime.strptime(message['sentDateTime'], "%Y-%m-%dT%H:%M:%SZ")
                                    self.env['mail.message'].create({
                                        'subject': message['subject'],
                                        'date': date,
                                        'body': message['bodyPreview'],
                                        'email_from': email_from,
                                        'partner_ids': [[6, 0, [to_partner.id]]],
                                        'attachment_ids': [[6, 0, attachment_ids]],
                                        'office_id': message['conversationId'],
                                        'author_id': from_partner.id,
                                        'model': 'res.partner',
                                        'res_id': to_partner.id
                                    })
                                    self.env.cr.commit()

            except Exception as e:
                raise ValidationError(_(str(e)))

    def generate_refresh_token(self):

        if self.env.user.refresh_token:
            settings = self.env['office.settings'].search([])
            settings = settings[0] if settings else settings

            if not settings.client_id or not settings.redirect_url or not settings.secret:
                raise osv.except_osv(_("Error!"), (_("Please ask admin to add Office365 settings!")))

            header = {
                'Content-Type': 'application/x-www-form-urlencoded'
            }

            response = requests.post(
                'https://login.microsoftonline.com/common/oauth2/v2.0/token',
                data='grant_type=refresh_token&refresh_token=' + self.env.user.refresh_token + '&redirect_uri=' + settings.redirect_url + '&client_id=' + settings.client_id + '&client_secret=' + settings.secret
                , headers=header).content

            response = json.loads((str(response)[2:])[:-1])
            if 'access_token' not in response:
                response["error_description"] = response["error_description"].replace("\\r\\n", " ")
                raise osv.except_osv(_("Error!"), (_(response["error"] + " " + response["error_description"])))
            else:
                self.env.user.token = response['access_token']
                self.env.user.refresh_token = response['refresh_token']
                self.env.user.expires_in = int(round(time.time() * 1000))
        else:
            print('Token is missing')


    def export_contacts(self):

        if self.env.user.token:
            try:
                if self.env.user.token:
                    if self.env.user.expires_in:
                        expires_in = datetime.fromtimestamp(int(self.env.user.expires_in) / 1e3)
                        expires_in = expires_in + timedelta(seconds=3600)
                        nowDateTime = datetime.now()
                        if nowDateTime > expires_in:
                            self.generate_refresh_token()

                    odoo_contacts = self.env['res.partner'].search([])
                    office_contact = []
                    count = 0
                    while True:

                        url = 'https://graph.microsoft.com/v1.0/me/contacts?$skip=' + str(count)

                        headers = {

                            'Host': 'outlook.office365.com',
                            'Authorization': 'Bearer {0}'.format(self.env.user.token),
                            'Accept': 'application/json',
                            'Content-Type': 'application/json',
                            'X-Target-URL': 'http://outlook.office.com',
                            'connection': 'keep-Alive'

                        }

                        response = requests.get(
                            url, headers=headers
                        ).content
                        response = json.loads(response.decode('utf-8'))
                        if not response['value']:
                            break

                        if 'value' in response:
                            contacts_emails = [response['value'][i]['emailAddresses'] for i in
                                               range(len(response['value']))]
                            for cont in contacts_emails:
                                if cont:
                                    office_contact.append(cont[0]['address'])

                        count += 10


                    for contact in odoo_contacts:

                        company = None

                        if contact.company_name:
                            company = contact.company_name
                        elif contact.parent_id.name:
                            company = contact.parent_id.name

                        data = {
                            "givenName": contact.name if contact.name else None,
                            'companyName': company,
                            'mobilePhone': contact.mobile if contact.mobile else None,
                            'jobTitle': contact.function if contact.function else None,
                            # 'homePhones' : ,
                            "businessPhones": [
                                contact.phone if contact.phone else None
                            ]
                        }
                        if contact.email:
                            data["emailAddresses"] = [
                                    {
                                        "address": contact.email,
                                    }
                                ]
                        if not contact.email and not contact.mobile and not contact.phone :
                            print(contact)
                            continue
                        if contact.email in office_contact:
                            continue
                        else :
                            post_response = requests.post(
                                url, data=json.dumps(data), headers=headers
                            ).content

                            if 'id' not in json.loads(post_response.decode('utf-8')).keys():
                                raise osv.except_osv(_("Error!"), (_(post_response["error"])))



                else:
                    raise UserWarning('Token is missing. Please Generate Token ')

            except Exception as e:
                raise ValidationError(_(str(e)))



    def import_contacts(self):
        """
        This is for importing contacts to office 365
        :return:
        """
        if self.env.user.token:
            try:
                if self.env.user.token:
                    if self.env.user.expires_in:
                        expires_in = datetime.fromtimestamp(int(self.env.user.expires_in) / 1e3)
                        expires_in = expires_in + timedelta(seconds=3600)
                        nowDateTime = datetime.now()
                        if nowDateTime > expires_in:
                            self.generate_refresh_token()
                    count = 0
                    while True:

                        url = 'https://graph.microsoft.com/v1.0/me/contacts?$skip=' + str(count)

                        headers = {

                            'Host': 'outlook.office365.com',
                            'Authorization': 'Bearer {0}'.format(self.env.user.token),
                            'Accept': 'application/json',
                            'Content-Type': 'application/json',
                            'X-Target-URL': 'http://outlook.office.com',
                            'connection': 'keep-Alive'

                        }

                        response = requests.get(
                            url, headers=headers
                        ).content
                        response = json.loads(response.decode('utf-8'))
                        if not response['value']:
                            break

                        office_contact_email = []
                        if 'value' in response:
                            for each_contact in response['value']:
                                if len(each_contact['emailAddresses']) > 0:
                                    if not self.env['res.partner'].search([('email', '=', each_contact['emailAddresses'][0]['address'])]):
                                        phone = None
                                        if len(each_contact['homePhones']) > 0:
                                            phone = each_contact['homePhones'][0]
                                        elif len(each_contact['businessPhones']) > 0:
                                            phone = each_contact['businessPhones'][0]

                                        self.env['res.partner'].create({
                                            'name': each_contact['displayName'],
                                            'email': each_contact['emailAddresses'][0]['address'],
                                            'company_name': each_contact['companyName'],
                                            'function': each_contact['jobTitle'],
                                            'mobile': each_contact['mobilePhone'],
                                            'phone': phone,
                                            'street': each_contact['homeAddress']['street'] if each_contact['homeAddress'] else None,
                                            'city': each_contact['homeAddress']['city'] if each_contact['homeAddress'] else None,
                                            'zip': each_contact['homeAddress']['postalCode'] if each_contact['homeAddress'] else None,
                                            'state_id': self.env['res.country.state'].search([('name', '=', each_contact['homeAddress']['state'])]).id if each_contact['homeAddress']  else None,
                                            'country_id': self.env['res.country'].search([('name', '=', each_contact['homeAddress']['countryOrRegion'])]).id if each_contact['homeAddress'] else None,
                                        })

                                elif each_contact['mobilePhone'] or len(each_contact['homePhones'])>0 or len(each_contact['businessPhones'])>0 :
                                    phone = None
                                    if len(each_contact['homePhones'])>0:
                                        phone = each_contact['homePhones'][0]
                                    elif len(each_contact['businessPhones'])>0:
                                        phone =each_contact['businessPhones'][0]

                                    if phone or each_contact['mobilePhone']:

                                        self.env['res.partner'].create({
                                            'name': each_contact['displayName'],
                                            'company_name': each_contact['companyName'],
                                            'function': each_contact['jobTitle'],
                                            'mobile': each_contact['mobilePhone'],
                                            'phone': phone,
                                            'street': each_contact['homeAddress']['street'] if each_contact[
                                                'homeAddress'] else None,
                                            'city': each_contact['homeAddress']['city'] if each_contact[
                                                'homeAddress'] else None,
                                            'zip': each_contact['homeAddress']['postalCode'] if each_contact[
                                                'homeAddress'] else None,
                                            'state_id': self.env['res.country.state'].search(
                                                [('name', '=', each_contact['homeAddress']['state'])]).id if each_contact[
                                                'homeAddress'] else None,
                                            'country_id': self.env['res.country'].search(
                                                [('name', '=', each_contact['homeAddress']['countryOrRegion'])]).id if
                                            each_contact['homeAddress'] else None,
                                        })

                        count +=10

                else:
                    raise UserWarning('Token is missing. Please Generate Token ')

            except Exception as e:
                raise ValidationError(_(str(e)))

        # raise osv.except_osv(_("Success!"), (_("Contacts are Successfully exported!!")))




class CustomMeeting(models.Model):
    """
    adding office365 event ID to ODOO meeting to remove duplication and facilitate updation
    """
    _inherit = 'calendar.event'


    office_id = fields.Char('Office365 Id')

#New mail code

class CustomMessageInbox(models.Model):
    """
    Email will store in mail.message class so that's why we need office_id
    """
    _inherit = 'mail.message'

    office_id = fields.Char('Office Id')


class CustomMessage(models.Model):

    # Email will be sent to the recipient of the message.

    _inherit = 'mail.mail'


    office_id = fields.Char('Office Id')
    # from_office = fields.Char(string= 'check')

    @api.model
    def create(self, values):
        """
        overriding create message to send email on message creation
        :param values:
        :return:
        """
        ################## New Code ##################
        ################## New Code ##################
        o365_id = None
        conv_id = None
        context = self._context

        current_uid = context.get('uid')

        user = self.env['res.users'].browse(current_uid)
        if user.send_mail_flag:
            if user.token:
                if user.expires_in:
                    expires_in = datetime.fromtimestamp(int(user.expires_in) / 1e3)
                    expires_in = expires_in + timedelta(seconds=3600)
                    nowDateTime = datetime.now()
                    if nowDateTime > expires_in:
                        self.generate_refresh_token()
                if 'mail_message_id' in values:
                    email_obj = self.env['mail.message'].search([('id', '=', values['mail_message_id'])])
                    partner_id = values['recipient_ids'][0][1]
                    partner_obj = self.env['res.partner'].search([('id', '=', partner_id)])

                    new_data = {
                                "subject": values['subject'] if values['subject'] else email_obj.body,
                                # "importance": "high",
                                "body": {
                                    "contentType": "HTML",
                                    "content": email_obj.body
                                },
                                "toRecipients": [
                                    {
                                        "emailAddress": {
                                            "address": partner_obj.email
                                        }
                                    }
                                ]
                            }

                    response = requests.post(
                        'https://graph.microsoft.com/v1.0/me/messages', data=json.dumps(new_data),
                                            headers={
                                                'Host': 'outlook.office.com',
                                                'Authorization': 'Bearer {0}'.format(user.token),
                                                'Accept': 'application/json',
                                                'Content-Type': 'application/json',
                                                'X-Target-URL': 'http://outlook.office.com',
                                                'connection': 'keep-Alive'
                                            })
                    if 'conversationId' in json.loads((response.content.decode('utf-8'))).keys():
                        conv_id = json.loads((response.content.decode('utf-8')))['conversationId']

                    if 'id' in json.loads((response.content.decode('utf-8'))).keys():

                        o365_id = json.loads((response.content.decode('utf-8')))['id']
                        if email_obj.attachment_ids:
                            for attachment in self.getAttachments(email_obj.attachment_ids):
                                attachment_response = requests.post(
                                    'https://graph.microsoft.com/beta/me/messages/' + o365_id + '/attachments',
                                    data=json.dumps(attachment),
                                    headers={
                                        'Host': 'outlook.office.com',
                                        'Authorization': 'Bearer {0}'.format(user.token),
                                        'Accept': 'application/json',
                                        'Content-Type': 'application/json',
                                        'X-Target-URL': 'http://outlook.office.com',
                                        'connection': 'keep-Alive'
                                    })
                        send_response = requests.post(
                            'https://graph.microsoft.com/v1.0/me/messages/' + o365_id + '/send',
                            headers={
                                'Host': 'outlook.office.com',
                                'Authorization': 'Bearer {0}'.format(user.token),
                                'Accept': 'application/json',
                                'Content-Type': 'application/json',
                                'X-Target-URL': 'http://outlook.office.com',
                                'connection': 'keep-Alive'
                            })

                        message = super(CustomMessage, self).create(values)
                        message.email_from = None

                        if conv_id:
                            message.office_id = conv_id

                        return message
                    else:
                        print('Check your credentials! Mail does not send due to invlide office365 credentials ')

                else:

                    return super(CustomMessage, self).create(values)

            else:
                print('Office354 Token is missing.. Please add your account token and try again!')
                return super(CustomMessage, self).create(values)

        else:
            return super(CustomMessage, self).create(values)



    def getAttachments(self, attachment_ids):
        attachment_list = []
        if attachment_ids:
            # attachments = self.env['ir.attachment'].browse([id[0] for id in attachment_ids])
            attachments = self.env['ir.attachment'].search([('id', 'in', [i.id for i in attachment_ids])])
            for attachment in attachments:
                attachment_list.append({
                    "@odata.type": "#microsoft.graph.fileAttachment",
                    "name": attachment.name,
                    "contentBytes": attachment.datas.decode("utf-8")
                })
        return attachment_list

    def generate_refresh_token(self):
        context = self._context

        current_uid = context.get('uid')

        user = self.env['res.users'].browse(current_uid)
        if user.refresh_token:
            settings = self.env['office.settings'].search([])
            settings = settings[0] if settings else settings

            if not settings.client_id or not settings.redirect_url or not settings.secret:
                raise osv.except_osv(_("Error!"), (_("Please ask admin to add Office365 settings!")))
            header = {
                'Content-Type': 'application/x-www-form-urlencoded'
            }


            response = requests.post(
                'https://login.microsoftonline.com/common/oauth2/v2.0/token',
                data='grant_type=refresh_token&refresh_token=' + user.refresh_token + '&redirect_uri=' + settings.redirect_url + '&client_id=' + settings.client_id + '&client_secret=' + settings.secret
                , headers=header).content

            response = json.loads((str(response)[2:])[:-1])
            if 'access_token' not in response:
                response["error_description"] = response["error_description"].replace("\\r\\n", " ")
                raise osv.except_osv(_("Error!"), (_(response["error"] + " " + response["error_description"])))
            else:
                user.token = response['access_token']
                user.refresh_token = response['refresh_token']
                user.expires_in = int(round(time.time() * 1000))
                self.env.cr.commit()


class CustomActivity(models.Model):
    _inherit = 'mail.activity'

    office_id = fields.Char('Office365 Id')

    @api.model
    def create(self, values):
        if self.env.user.expires_in:
            expires_in = datetime.fromtimestamp(int(self.env.user.expires_in) / 1e3)
            expires_in = expires_in + timedelta(seconds=3600)
            nowDateTime = datetime.now()
            if nowDateTime > expires_in:
                self.generate_refresh_token()

        o365_id = None
        if self.env.user.office365_email and not self.env.user.is_task_sync_on and values[
            'res_id'] == self.env.user.partner_id.id:
            data = {
                'subject': values['summary'] if values['summary'] else values['note'],
                "body": {
                    "contentType": "html",
                    "content": values['note']
                },
                "dueDateTime": {
                    "dateTime": values['date_deadline'] + 'T00:00:00Z',
                    "timeZone": "UTC"
                },
            }
            response = requests.post(
                'https://graph.microsoft.com/beta/me/outlook/tasks', data=json.dumps(data),
                headers={
                    'Host': 'outlook.office.com',
                    'Authorization': 'Bearer {0}'.format(self.env.user.token),
                    'Accept': 'application/json',
                    'Content-Type': 'application/json',
                    'X-Target-URL': 'http://outlook.office.com',
                    'connection': 'keep-Alive'
                }).content
            if 'id' in json.loads((response.decode('utf-8'))).keys():
                o365_id = json.loads((response.decode('utf-8')))['id']

        """
        original code!
        """

        activity = super(CustomActivity, self).create(values)
        self.env[activity.res_model].browse(activity.res_id).message_subscribe(
            partner_ids=[activity.user_id.partner_id.id])
        if activity.date_deadline <= fields.Date.today():
            self.env['bus.bus'].sendone(
                (self._cr.dbname, 'res.partner', activity.user_id.partner_id.id),
                {'type': 'activity_updated', 'activity_created': True})
        if o365_id:
            activity.office_id = o365_id
        return activity

    def generate_refresh_token(self):

        if self.env.user.refresh_token:
            settings = self.env['office.settings'].search([])
            settings = settings[0] if settings else settings

            if not settings.client_id or not settings.redirect_url or not settings.secret:
                raise osv.except_osv(_("Error!"), (_("Please ask admin to add Office365 settings!")))

            header = {
                'Content-Type': 'application/x-www-form-urlencoded'
            }

            response = requests.post(
                'https://login.microsoftonline.com/common/oauth2/v2.0/token',
                data='grant_type=refresh_token&refresh_token=' + self.env.user.refresh_token + '&redirect_uri=' + settings.redirect_url + '&client_id=' + settings.client_id + '&client_secret=' + settings.secret
                , headers=header).content

            response = json.loads((str(response)[2:])[:-1])
            if 'access_token' not in response:
                response["error_description"] = response["error_description"].replace("\\r\\n", " ")
                raise osv.except_osv(("Error!"), (response["error"] + " " + response["error_description"]))
            else:
                self.env.user.token = response['access_token']
                self.env.user.refresh_token = response['refresh_token']
                self.env.user.expires_in = int(round(time.time() * 1000))

    @api.multi
    def unlink(self):
        for activity in self:
            if activity.office_id:
                response = requests.delete(
                    'https://graph.microsoft.com/beta/me/outlook/tasks/' + activity.office_id,
                    headers={
                        'Host': 'outlook.office.com',
                        'Authorization': 'Bearer {0}'.format(self.env.user.token),
                        'Accept': 'application/json',
                        'Content-Type': 'application/json',
                        'X-Target-URL': 'http://outlook.office.com',
                        'connection': 'keep-Alive'
                    })
                if response.status_code != 204 and response.status_code != 404:
                    raise osv.except_osv(_("Office365 SYNC ERROR"), (_("Error: " + str(response.status_code))))
            if activity.date_deadline <= fields.Date.today():
                self.env['bus.bus'].sendone(
                    (self._cr.dbname, 'res.partner', activity.user_id.partner_id.id),
                    {'type': 'activity_updated', 'activity_deleted': True})
        return super(CustomActivity, self).unlink()


