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
		for lead in self:
			out = 0
			if lead.partner_id.show_senior_number:
				out += lead.partner_id.senior_number

			lead.senior_number = out

	@api.depends('senior_number')
	def _compute_senior_number_string(self):
		for lead in self:
			if lead.senior_number != 0:
				lead.senior_number_string = 'mit ' + str(lead.senior_number) + ' Senioren'
			else:
				lead.senior_number_string = ''
