import logging

from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class linderaMail(models.Model):
	_inherit = 'mail.message'
	o365ID = fields.Char('o365ID')
	o365ConversationID = fields.Char('o365ConversationID')

