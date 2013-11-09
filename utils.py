# anything else we're sharing amongst jTime Tempo and ActivityStream
class JTUtils():

	# retrieve a dict from a list of dicts based on a key value pair
	#
	# l: list of dicts
	# k: key to search
	# v: value of k
	#
	# returns dict if found, else none
	def get_from_dict(self,l,k,v):

		i = iter(d for d in l if d[k] == v)

		try:
			return next(i)
		except StopIteration:
			return None
		finally:
			del i


from bs4      import BeautifulSoup
from datetime import *
import re

# wrapper for BeautifulSoup with some helper fns for Jira
class JTHTMLUtils():

	# html - html string you want to use with this instance
	#        of the parser
	def __init__(self, html, config):

		self.html   = html
		# we need to use html5 parsing with Jira, as the HTML is not valid
		self.soup   = BeautifulSoup(self.html,'html5')
		self.config = config
		self.jira   = JiraUtils(config)

	# check whether or not the user is logged in based on the response body
	def is_logged_in(self):

		# TODO - we could do more with this (the CAPTCHA)
		err_div = self.soup.find_all('div', class_='aui-message error')

		if not len(err_div):
			return True

		return False

	# parse the tempo timesheet HTML table
	#
	# returns a list of ticket dicts parsed out of the html
	def parse_tempo_html(self):

		# grab the tempo issue table
		issues = self.soup.find(id='issuetable')

		# find the headers (which we base extraction on)
		heads  = issues.find('thead').find_all('th')

		issue_idx  = -1
		worked_idx = -1
		head_idx   = 0
		tickets    = []

		for head in heads:
			if head.get_text().strip() == 'Issue':
				issue_idx = head_idx

			if head.get_text().strip() == 'Worked':
				# for some reason it's -1
				worked_idx = head_idx -1

			head_idx += 1

		# blow up if we didn't find stuff
		if issue_idx == -1 or worked_idx == -1:
			raise jTimeError('TEMPO_PARSE')

		rows = issues.find_all("tr")

		# iterate the table rows and grab what we need
		for row in rows:

			# iterate columns
			cols        = row.find_all("td")
			col_idx     = 0
			ticket      = None

			for col in cols:

				if col_idx == issue_idx:

					issue_class = " ".join(col['class'])

					if issue_class != "nav summary expanded":
						col_idx += 1
						continue

					# if we've got this far its a relevant row (ticket rather than random tempo thing)
					ticket = self.jira.build_ticket_dict(
						self.jira.parse_ticket_id(col.get_text().strip())
					)

				if col_idx == worked_idx - 1 and ticket is not None:
					ticket['time'] = self.jira.convert_tempo_time(float(col.get_text().strip()))
					tickets.append(ticket)

				col_idx +=1

		return tickets


from shared.utils import HTTPUtils
from jtime_error  import jTimeError

# Jira specific utilities that apply to both tempo and activity stream
class JiraUtils():

	def __init__(self, config, http_utils=None):
		self.config     = config
		self.http_utils = http_utils
		self.session_cookie = self.config.get('jira','jira_sess_cookie')
		self.csrf_cookie    = self.config.get('jira','jira_csrf_cookie')

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

	#
	# Public Functions
	#

	# login to Jira (standard web login)
	#
	# username: Jira username
	# password: Jira password
	#
	# returns session cookie dict (as per _check_session)
	def login(self, username, password):

		url = self.config.get('jira','jira_url') + '/login.jsp'

		request_params = {
			'os_username': username,
			'os_password': password
		}

		resp     = self.http_utils.do_req(url, request_params)
		resp_str = resp['response_string']

		# this will blow up if we're not logged in
		cookies = self._check_session(resp['cookie_jar'])

		html = JTHTMLUtils(resp_str,self.config)

		if not html.is_logged_in():
			raise jTimeError('BAD_J_USER')

		return cookies

	# build a dict from parse_ticket_id
	#
	# ticket_detail: return value of _parse_ticket_id
	#
	# returns: {
	#     'project': LBR,
	#     'ticket_id': LBR-12345,
	#     'time': None
	# }
	def build_ticket_dict(self, ticket_detail):

		project     = ticket_detail['project']
		ticket_id   = project + '-' + ticket_detail['ticket_id']

		return {
			'project': project,
			'ticket_id': ticket_id,
			'time': timedelta()
		}

	# grab a Jira ticket ID from a string
	#
	# string: containing the ticket_id
	#
	# return {
	#     'project': LBR,
	#     'ticket_id': LBR-12345
	# }
	def parse_ticket_id(self, string):

		rexp      = self.config.get('jira','ticket_regexp')
		match     = re.search(rexp,string)

		if match is None:
			raise jTimeError('NO_TICKET_ID', string)

		try:
			project   = match.group(1)
			ticket_id = match.group(2)
		except Exception as e:
			raise jTimeError('BAD_TITLE', title_detail)

		return {
			'project': project,
			'ticket_id': ticket_id
		}

	# convert a tempo time (0.40) to a python timedelta
	#
	# time: tempo time
	#
	# return python timedelta
	def convert_tempo_time(self,time):

		hours   = int(time)
		m       = 60 * (time-hours)
		minutes = int(m)
		seconds = int(60 * (m-minutes))

		return timedelta(
			hours=hours,
			minutes=minutes,
			seconds=seconds
		)

