from odoo import models, fields, api

class LinderaHome(models.Model):
	"""
	Add more fields and functions to the home
	"""
	_inherit = 'res.partner'

	senior_number = fields.Integer('senior_number')
	show_senior_number = fields.Boolean('show_senior_number')
	
	first_name = fields.Char(compute='_compute_first_name', readonly=False)
	last_name = fields.Char(compute='_compute_last_name', readonly=False)

	@api.model
	def create(self, values):
		"""
		Creates a new contact instance. Wraps existing method.
		:param values: initial values of the event
		:return: returns an event
		"""

		contact = super(LinderaHome, self).create(values)

		if 'category_id' in values.keys():
			isEinrichtung = False
			for id in values['category_id'][0][2]:
				cat = contact.env['res.partner.category'].browse(id)
				if cat.name == 'Einrichtung':
					isEinrichtung = True
			contact.show_senior_number = isEinrichtung
			if not isEinrichtung:
				contact.senior_number = 0

		return contact

	def write(self, values):
		"""
		Is called whenever a field is changed (even during initialization!).
		:param values: changed fields
		:return: bool writeSuccess
		"""
		for home in self:
			if 'category_id' in values.keys():
				isEinrichtung = False
				for id in values['category_id'][0][2]:
					cat = self.env['res.partner.category'].browse(id)
					if cat.name == 'Einrichtung':
						isEinrichtung = True
				home.show_senior_number = isEinrichtung
				if not isEinrichtung:
					home.senior_number = 0

		super(LinderaHome, self).write(values)
		
	@api.depends('name', 'is_company')
	def _compute_first_name(self):
		for partner in self:
			if not partner.is_company:
				if ' ' in partner.name:
					partner.first_name = partner.name.split(' ')[0]
				else:
					partner.first_name = ''
			else:
				partner.first_name = ''
	
	@api.depends('name', 'is_company')
	def _compute_last_name(self):
		for partner in self:
			if not partner.is_company:
				if ' ' in partner.name:
					partner.last_name = partner.name.split(' ')[1]
				else:
					partner.last_name = ''
			else:
				partner.last_name = ''
