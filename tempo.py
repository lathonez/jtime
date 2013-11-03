from jtime_error  import jTimeError
from utils        import JTHTMLUtils, JiraUtils
from shared.utils import HTTPUtils
import feedparser, re, ConfigParser

class Tempo():

	def __init__ (self, config):

		self.config         = config
		self.http_utils     = HTTPUtils(self.config)
		self.jira           = JiraUtils(config,self.http_utils)

	# grab the tempo report html for a given date and parse it
	#
	# date -    python datetime
	# cookies - cookies from login
	#
	# returns list of ticket dicts
	def _get_tickets(self, date, cookies):

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
			self.config.get('jira','jira_sess_cookie'),
			cookies['session'],
			self.config.get('jira','jira_cookie_dom')
		)

		xc = self.http_utils.set_cookie(
			self.config.get('jira','jira_csrf_cookie'),
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
		html     = JTHTMLUtils(resp_str,self.config)

		tickets = html.parse_tempo_html()

		if not len(tickets):
			raise jTimeError('NO_ACTIVITIES')

		# sort the results
		return sorted(tickets, key=lambda k: k['ticket_id'])
	
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
	def get_tickets(self, username, password, date):

		cookies = self.jira.login(username, password)
		return self._get_tickets(date, cookies)

