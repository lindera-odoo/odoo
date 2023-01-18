import os
from odoo import models, api, fields
from O365 import Account, FileSystemTokenBackend
import odoo
from .odooTokenStore import odooTokenStore

# CLIENT_ID = '91ff48ec-0d1a-46b0-ba2b-3eca18e64eae'
# CLIENT_SECRET = 'b6sb0kW]mingcb=:f0/GdO0dJ5v@p]jz'
# CALLBACK_URL = 'http://localhost:8069/'


class Office365UserSettings(models.Model):
    _name = 'lindera.auth.usersettings'

    @api.model
    def view_init(self, *args):
        self.env.user.auth_url = odoo.http.request.httprequest.referrer

    def authFirstStep(self):
        CLIENT_ID = self.env['ir.config_parameter'].get_param('lindera.client_id')
        CLIENT_SECRET = self.env['ir.config_parameter'].get_param('lindera.client_secret')
        CALLBACK_URL = self.env['ir.config_parameter'].get_param('lindera.callback_url')

        account = Account((CLIENT_ID, CLIENT_SECRET))
        url, self.env.user.auth_state = account.con.get_authorization_url(
            requested_scopes=account.protocol.get_scopes_for(['basic', 'message_all', 'address_book_all',
                                                              'address_book_all_shared', 'calendar_all',
                                                              'calendar_shared_all']),
            redirect_uri=CALLBACK_URL)
        return {
            'type': 'ir.actions.act_url',
            'url': url,
            'target': 'self',
            'res_id': self.id,
        }

    def authSecondStep(self):
        CLIENT_ID = self.env['ir.config_parameter'].get_param('lindera.client_id')
        CLIENT_SECRET = self.env['ir.config_parameter'].get_param('lindera.client_secret')
        CALLBACK_URL = self.env['ir.config_parameter'].get_param('lindera.callback_url')

        path = os.path.abspath(os.path.dirname(__file__) + '/../tokens')
        token_backend = odooTokenStore(self.env.user)
        token_backend.delete_token()
        account = Account((CLIENT_ID, CLIENT_SECRET), token_backend=token_backend)
        account.con.token_backend = token_backend

        # dirty fix so that it also accepts redirect to http for testing reasons...
        url = self.env.user.auth_url
        if not 'https' in url:
            url = url.replace('http', 'https')


        result = account.con.request_token(url,
                                           state=self.env.user.auth_state,
                                           redirect_uri=CALLBACK_URL)
        if result:
            return {
                'type': 'ir.actions.act_url',
                'url': CALLBACK_URL,
                'target': 'self',
                'res_id': self.id,
            }
