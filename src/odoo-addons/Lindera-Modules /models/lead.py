from odoo import models, fields, api


class Linderlead(models.Model):
	"""
	Add more fields and functions to the leads
	"""
	_inherit = 'crm.lead'

	senior_number_string = fields.Char(compute='_compute_senior_number_string',
	                            help='String Containing Senior Number or empty string',
	                            store=True)

	senior_number = fields.Integer(compute='_compute_senior_number',
	                               help='String Containing Senior Number or empty string',
	                               store=True)

	@api.depends('partner_id', 'partner_id.senior_number', 'partner_id.show_senior_number')
	def _compute_senior_number(self):
		out = 0
		if self.partner_id.show_senior_number:
			out += self.partner_id.senior_number

		self.senior_number = out

	@api.depends('senior_number')
	def _compute_senior_number_string(self):
		if self.senior_number != 0:
			self.senior_number_string = 'mit ' + str(self.senior_number) + ' Senioren'
		else:
			self.senior_number_string = ''
