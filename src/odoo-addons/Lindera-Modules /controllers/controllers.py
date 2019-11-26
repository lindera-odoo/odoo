# -*- coding: utf-8 -*-
from odoo import http

# class Custom-addons/contactsCreateHome(http.Controller):
#     @http.route('/custom-addons/contacts_create_home/custom-addons/contacts_create_home/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/custom-addons/contacts_create_home/custom-addons/contacts_create_home/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('custom-addons/contacts_create_home.listing', {
#             'root': '/custom-addons/contacts_create_home/custom-addons/contacts_create_home',
#             'objects': http.request.env['custom-addons/contacts_create_home.custom-addons/contacts_create_home'].search([]),
#         })

#     @http.route('/custom-addons/contacts_create_home/custom-addons/contacts_create_home/objects/<model("custom-addons/contacts_create_home.custom-addons/contacts_create_home"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('custom-addons/contacts_create_home.object', {
#             'object': obj
#         })