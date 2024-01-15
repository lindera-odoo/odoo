from odoo import models, fields, api

class LinderaHome(models.Model):
	"""
	Add more fields and functions to the home
	"""
	_inherit = 'res.partner'

	senior_number = fields.Integer('senior_number')
	show_senior_number = fields.Boolean('show_senior_number')
	
	first_name = fields.Char(compute='_compute_form_of_address', readonly=False)
	last_name = fields.Char(compute='_compute_form_of_address', readonly=False)
	form_of_address = fields.Char(compute='_compute_form_of_address', readonly=False)

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
			
			form_of_address_keys = {'first_name', 'last_name', 'form_of_address'}.intersection(values.keys())
			if len(form_of_address_keys) != 0:
				form_of_address = self.env['lindera.address'].search([("contact_id", "=", home.id)])
				if form_of_address:
					filtered_values = {key: values[key] for key in form_of_address_keys}
					form_of_address.write(filtered_values)

		super(LinderaHome, self).write(values)
		
	def _compute_form_of_address(self):
		for partner in self:
			if partner.id:
				if not partner.is_company:
					form_of_address = self.env['lindera.address'].search([("contact_id", "=", partner.id)])
					if form_of_address:
						partner.first_name = form_of_address.first_name
						partner.last_name = form_of_address.last_name
						partner.form_of_address = form_of_address.form_of_address
					else:
						if ' ' in partner.name:
							first_name = partner.name.split(' ')[0]
							last_name = partner.name.split(' ')[1]
						else:
							first_name = ''
							last_name = ''
						
						partner.first_name = first_name
						partner.last_name = last_name
						partner.form_of_address = ''
						
						self.env['lindera.address'].create({
							'contact_id': partner.id,
							'first_name': first_name,
							'last_name': last_name,
							'form_of_address': ''
						})
				else:
					partner.first_name = ''
					partner.last_name = ''
					partner.form_of_address = ''