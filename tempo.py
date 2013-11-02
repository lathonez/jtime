from shared.utils import HTTPUtils
import feedparser, re, ConfigParser

class Tempo():

	def __init__ (self, config):

		self.config         = config
		self.http_utils     = HTTPUtils(self.config)

	def _login(self, username, password):

		url = self.config.get('app','jira_url') + '/login.jsp'

		request_params = {
			'os_username': username,
			'os_password': password
		}

		resp     = self.http_utils.do_req(url, request_params)
		resp_str = resp['response_string']

		print resp_str

		# this will blow up if we're not logged in
		self._check_session(resp['cookie_jar'])

		return true
		
	# Throws an exception if we're not logged in to Jira
	def _check_session(self, cookie_jar):

		session_cookie = self.config.get('app','jira_sess_cookie')
		csrf_cookie    = self.config.get('app','jira_csrf_cookie')

		# we should have a session cookie and a CSRF token
		session = self.http_utils.get_cookie(cookie_jar, session_cookie)
		csrf    = self.http_utils.get_cookie(cookie_jar, csrf_cookie)

		if session is None or csrf is None:
			raise jTimeError('BAD_J_USER')

		return {
			'session': session,
			'csrf': csrf
		}

