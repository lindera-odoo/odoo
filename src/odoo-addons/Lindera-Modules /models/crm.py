# from odoo import models, fields, api
# from . import backend_client
# from datetime import datetime
# from openerp.osv import osv


# def getCurrentTimestamp():
#     return datetime.now().timestamp().__round__()


# class LinderaCRM(models.Model):
#     _inherit = 'crm.lead'

#     @api.multi
#     def write(self, vals):
#         result = super(LinderaCRM, self).write(vals)

#         # TODO I think you mean vals.keys()... this probably still works, when there is a value with stage_id doesn't it?
#         if 'stage_id' not in vals:
#             return

#         id = vals['stage_id']
#         findStageById = self.env['crm.stage'].search([('id', '=', id)])
#         name = findStageById.name
#         # Get the current timestamp in seconds
#         cts = getCurrentTimestamp()

#         # TODO might want to make this a class method, since it even accesses self...
#         def checkIfHomeExists():
#             # Get associated partner's (contact/home/compnay) data
#             partnerId = self.read()[0]['partner_id'][0]

#             # Check if the contact exists in lindera backend
#             homeData = backend_client.getHome(partnerId).json()
#             if homeData['total'] == 0 and len(homeData['data']) == 0:
#                 raise osv.except_osv(
#                     ('Error!'), ('The associated partner does not exist in Lindera database, please create it first'))
#             else:
#                 mongoId = homeData['data'][0]['_id']
#                 return mongoId
#         # TODO maybe this one too. It just makes it more reusable especially if the models need to work with each other
#         def update(id, field):
#             updatedField = {
#                 'subscriptionEndDate': field
#             }
#             return backend_client.updateHome(id, updatedField)

#         if name == '8 W-Test live' or name == 'Einführung':
#             mID = checkIfHomeExists()

#             futureTs = cts + (60 * 60 * 24 * 70)
#             expirationDate = datetime.fromtimestamp(futureTs).isoformat()
#             update(mID, expirationDate)

#         if name == 'On hold':
#             mID = checkIfHomeExists()

#             pastTs = cts - (60 * 60 * 24)
#             expirationDate = datetime.fromtimestamp(pastTs).isoformat()
#             update(mID, expirationDate)

#         return result
