import os
from odoo import models, api
from O365 import Account, FileSystemTokenBackend

CLIENT_ID = os.getenv('CLIENT_ID')
CLIENT_SECRET = os.getenv('CLIENT_SECRET')
CALLBACK_URL = os.getenv('CALLBACK_URL')

class Office365UserSettings(models.Model):
	_name = 'lindera.auth.usersettings'

	@api.one
	def authFirstStep(self):
		account = Account((CLIENT_ID, CLIENT_SECRET))
		self.env.user.state = account.con.get_authorization_url(requested_scopes=['basic', 'message_all'], redirect_uri=CALLBACK_URL)[0]

	@staticmethod
	def __state():
		account = Account((CLIENT_ID, CLIENT_SECRET))
		return account.con.get_authorization_url(requested_scopes=['basic', 'message_all'], redirect_uri=CALLBACK_URL)[1]


