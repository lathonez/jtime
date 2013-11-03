from jtime_error  import jTimeError
from utils        import JTHTMLUtils
from shared.utils import HTTPUtils
import feedparser, re, ConfigParser

class Tempo():

	def __init__ (self, config):

		self.config         = config
		self.http_utils     = HTTPUtils(self.config)
		self.session_cookie = self.config.get('jira','jira_sess_cookie')
		self.csrf_cookie    = self.config.get('jira','jira_csrf_cookie')

	# login to Jira (standard web login)
	#
	# username: Jira username
	# password: Jira password
	#
	# returns session cookie dict (as per _check_session)
	def _login(self, username, password):

		url = self.config.get('jira','jira_url') + '/login.jsp'

		request_params = {
			'os_username': username,
			'os_password': password
		}

		resp     = self.http_utils.do_req(url, request_params)
		resp_str = resp['response_string']

		# this will blow up if we're not logged in
		cookies = self._check_session(resp['cookie_jar'])

		html = JTHTMLUtils(resp_str)

		if not html.is_logged_in():
			raise jTimeError('BAD_J_USER')

		return cookies

	# grab the tempo report html for a given date and parse it
	#
	# date -    python datetime
	# cookies - cookies from login
	#
	# returns ?
	def _parse_time_html(self, date, cookies):

		url = self.config.get('jira','jira_url') + '/secure/TempoUserBoard!report.jspa'

		# 2/Nobember/2013
		exact = '{0}/{1}/{2}'.format(
			date.day,
			date.strftime("%B"),
			date.year
		)

		request_params = {
			'periodView': 'DAY',
			'exact': exact
		}

		sc = self.http_utils.set_cookie(
			self.session_cookie,
			cookies['session'],
			self.config.get('jira','jira_cookie_dom')
		)

		xc = self.http_utils.set_cookie(
			self.csrf_cookie,
			cookies['csrf'],
			self.config.get('jira','jira_cookie_dom')
		)

		resp = self.http_utils.do_req(
			url=url,
			data=request_params,
			post=False,
			cookies = [sc,xc]
		)

		resp_str = resp['response_string']
	
		print resp_str
	
	# Throws an exception if we've not got some session cookies
	#
	# cookie_jar - cookielib CookieJar
	#
	# returns: {
	#     'session': session cookie value,
	#     'csrf':    crsf cookie value
	# }
	def _check_session(self, cookie_jar):

		# we should have a session cookie and a CSRF token
		session = self.http_utils.get_cookie(cookie_jar, self.session_cookie)
		csrf    = self.http_utils.get_cookie(cookie_jar, self.csrf_cookie)

		if session is None or csrf is None:
			raise jTimeError('BAD_J_USER')

		return {
			'session': session,
			'csrf': csrf
		}

	# Fully parse a HTML time report from tempo
	#
	# username: Jira username
	# password: Jira password
	# date:     datetime obj
	#
	# returns: {
	#     'tickets': tickets,
	#     'projects': projects,
	#     'summary': {total_time: '07:30:59', total_tenrox_time: '7.5'}
	# }
	def get_time(self, username, password, date):

		cookies = self._login(username, password)
		self._parse_time_html(date, cookies)

		return {
			'tickets': None,
			'projects': None,
			'summary': None
		}

