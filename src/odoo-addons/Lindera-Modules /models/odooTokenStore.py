from O365.utils import BaseTokenBackend
import json


class odooTokenStore(BaseTokenBackend):
	def __init__(self, user):
		self._user = user
		super(odooTokenStore, self).__init__()

	def load_token(self):
		self.token = json.loads(self._user.auth_token)
		return self.token

	def save_token(self):
		self._user.auth_token = json.dumps(self.token)
		return True

	def delete_token(self):
		self._user.auth_token = ''
		return True

	def check_token(self):
		try:
			return self._user.auth_token != '' and self._user.auth_token is not None and self._user.auth_token is not False
		except:
			return False