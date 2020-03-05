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

	start_date = fields.Date('start_date')
	end_date = fields.Date('end_date')

	date_string = fields.Char(compute='_compute_date_string',
	                          help='String Containing the start and end Date of a Contract',
	                          store=True)
	show_dates = fields.Boolean(compute='_compute_show_dates', store=True)

	@api.depends('partner_id', 'partner_id.senior_number', 'partner_id.show_senior_number', 'partner_id.category_id')
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
				lead.senior_number_string = 'mit ' + str(lead.senior_number) + ' Senioren\n'
			else:
				lead.senior_number_string = ''

	@api.depends('start_date', 'end_date', 'show_dates')
	def _compute_date_string(self):
		for lead in self:
			if lead.start_date and lead.end_date and lead.show_dates:
				lead.date_string = str(lead.start_date) + ' - ' + str(lead.end_date)
			else:
				lead.date_string = ''

	@api.depends('partner_id', 'partner_id.category_id')
	def _compute_show_dates(self):
		for lead in self:
			lead.show_dates = False
			for cat in lead.partner_id.category_id:
				if cat.name == 'Versicherung':
					lead.show_dates = True