from odoo import models, fields, api


class Linderlead(models.Model):
	"""
	Add more fields and functions to the leads
	"""
	_inherit = 'crm.lead'

	senior_number_string = fields.Char(compute='_compute_senior_number_string',
	                            help='string containing senior number or empty string',
	                            store=True)

	senior_number = fields.Integer(compute='_compute_senior_number',
	                               help='string containing senior number or empty string',
	                               store=True)
	
	home_id = fields.Text(compute='_compute_home_id', store=False)

	start_date = fields.Date('start_date')
	end_date = fields.Date('end_date')
	
	introduction_date = fields.Date('introduction_date')

	date_string = fields.Char(compute='_compute_date_string',
	                          help='string containing the start and end date of a contract',
	                          store=True)
	show_dates = fields.Boolean(compute='_compute_show_dates', store=True)
	
	show_introduction_date = fields.Boolean(compute='_compute_show_introduction_date', store=True)
	
	create_users = fields.Many2many('res.partner', string='Users', track_visibility='onchange', track_sequence=1, index=True,
        help="Users to automatically create in the backend")
	
	carrier = fields.Many2one('res.partner', string='Träger', track_visibility='onchange', track_sequence=1,
								 index=True,
								 help="Contact that pays for the contract/chance")

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
				
	@api.depends('partner_id', 'partner_id.homeID')
	def _compute_home_id(self):
		for lead in self:
			lead.home_id = lead.partner_id.homeID

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
				if cat.name in ['Versicherung', 'Einrichtung']:
					lead.show_dates = True
	
	@api.depends('partner_id', 'partner_id.category_id')
	def _compute_show_introduction_date(self):
		for lead in self:
			lead.show_introduction_date = False
			for cat in lead.partner_id.category_id:
				if cat.name == 'Einrichtung':
					lead.show_introduction_date = True