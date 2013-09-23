from utils        import HTTPUtils
from time         import mktime
from datetime     import datetime
import feedparser, re, ConfigParser

# Class to obtain and parse an activity stream from Jira
class ActivityStream():

	def __init__ (self, config):

		self.config = config
		self.http_utils = HTTPUtils(self.config)

	# get the activity stream for a given user
	#
	# username: Jira username
	# password: Jira password
	#
	# return: feedparsed activiy stream
	def _get_stream(self, username, password):

		url      = self.config.get('app','base_url')
		auth     = self.config.get('app','auth_type')
		results  = self.config.get('app','results')
		streams  = 'user+IS+{0}'.format(username)

		print 'get_stream: Attemptint to get stream for user',username

		request_params = {
			'maxResults': results,
			'streams': streams,
			'os_authType': auth
		}

		try:
			resp = self.http_utils.do_req(
				url=url,
				data=request_params,
				post=False,
				username=username,
				password=password,
				url_encode=False
			)
		except Exception as e:

			# check for failed login
			if str(e).index('HTTP error code: 401'):
				raise ActivityStreamError('BAD_USER')
			else:
				raise e

		print 'get_stream: Stream received from Jira, parsing..'

		stream = feedparser.parse(resp['response_string'])

		return stream

	# parse the stream:
	#  - newest events are first in the stream
	#  - pull out relevant entries
	#  - find unique tickets from entries
	#  - sum the time up for each ticket
	#
	# stream: feedparsed activity stream
	# day:    day of the month (e.g. 26)
	# month:  month of the year (e.g. 09)
	#
	# return: list of ticket dicts
	def _parse_stream(self, stream, day, month):

		fn      = '_parse_stream:'
		day     = int(day)
		month   = int(month)
		entries = []
		tickets = []

		# find relevant entries
		for entry in stream.entries:

			e_day = int(entry.published_parsed.tm_mday)
			e_month = int(entry.published_parsed.tm_mon)

			if day == e_day and month == e_month:
				entries.append(entry)

		if not len(entries):
			raise ActivityStreamError('NO_ACTIVITIES')

		print fn,len(entries),'events found'

		# debug available time
		start = entries[0]
		end   = entries[len(entries)-1]
		avail = self._get_time_difference(start,end)
		print fn,'Time Available:',avail

		prev_entry  = None
		prev_ticket = None

		for entry in entries:

			try:
				# temp ticket to test with
				t = self._build_ticket_dict(entry)
			except ActivityStreamError as e:
				# we've got a random event like 'linked two tickets', ignore
				if e.code == 'NO_TICKET_ID':
					print fn,'skipping entry @',entry.published
					continue
				else:
					raise e

			exists = self._get_from_dict(tickets,'ticket_id',t['ticket_id'])

			# if we've not seen this ticket yet, add it
			if exists is None:
				tickets.append(t)
			else:
				t = exists

			# first event, we can't do anything here
			if prev_entry is None:
				prev_entry = entry
				prev_ticket = t
				continue

			# what's the time differnce?
			diff = self._get_time_difference(prev_entry, entry)

			# this time difference is applied to the previous event
			# we're moving back through time in this loop
			if prev_ticket['time'] is None:
				prev_ticket['time'] = diff
			else:
				prev_ticket['time'] += diff

			prev_entry = entry
			prev_ticket = t

		# sanity check time
		total_time = self._get_total_time(tickets,False)
		if total_time != avail:
			raise ActivityStreamError('BAD_TIME','total_time: {0}, avail: {1}'.format(total_time,avail))
		else:
			print fn,total_time,'accounted for'

		return tickets

	# work out the (published) time difference between two rss entries
	#
	# entry1: first entry in the stream (latest)
	# entry2: subsequent entry in the stream (older than entry 1)
	#
	# return datetime object representing the time difference
	def _get_time_difference(self, entry1, entry2):

		time1 = datetime.fromtimestamp(mktime(entry1.published_parsed))
		time2 = datetime.fromtimestamp(mktime(entry2.published_parsed))
		diff  = time1 - time2

		return diff

	# build a dict from an rss entry
	#
	# entry: rss entry
	#
	# returns: {
	#     'project': LBR,
	#     'ticket_id': LBR-12345,
	#     'time': None
	# }
	def _build_ticket_dict(self,entry):

		td          = self._parse_title_detail(entry.title_detail.value)
		project     = td['project']
		ticket_id   = project + '-' + td['ticket_id']

		return {
			'project': project,
			'ticket_id': ticket_id,
			'time': None
		}

	# parse the rss title detail into useful info
	#
	# rss entry .title_detail.value
	#
	# return {
	#     'project': LBR,
	#     'ticket_id': LBR-12345
	# }
	def _parse_title_detail(self, title_detail):

		jira_link = 'https://jira.openbet.com/browse/'
		rexp      = '([A-Z][A-Z][A-Z]?)-([1-9][0-9]*)'
		idx       = title_detail.find(jira_link) + len(jira_link)
		jira_id   = title_detail[idx:idx+9]
		match     = re.search(rexp,jira_id)

		if match is None:
			raise ActivityStreamError('NO_TICKET_ID', title_detail)

		try:
			project   = match.group(1)
			ticket_id = match.group(2)
		except Exception as e:
			raise ActivityStreamError('BAD_TITLE', title_detail)

		return {
			'project': project,
			'ticket_id': ticket_id
		}

	# derive the tenrox code from a project
	#
	# project: Jira project (LBR)
	#
	# returns: tenrox code (LBR300)
	def _get_tenrox_code(self, project):

		try:
			code = self.config.get('tenrox_codes',project)
		except ConfigParser.NoOptionError:
			code = project + '300'

		return code

	# retrieve a dict from a list of dicts based on a key value pair
	#
	# l: list of dicts
	# k: key to search
	# v: value of k
	#
	# returns dict if found, else none
	def _get_from_dict(self,l,k,v):

		i = iter(d for d in l if d[k] == v)

		try:
			return next(i)
		except StopIteration:
			return None
		finally:
			del i

	# get the total across all tickets
	#
	# tickets: list of ticket dicts
	# debug:   print the following info whilst summing
	#  - for each ticket: ticket_id, time
	#  - total time when completed
	#
	# returns datetime object containing the total time (convenience)
	def _get_total_time(self,tickets,debug=False):

		total_time = None

		for ticket in tickets:

			if debug:
				print ticket['ticket_id'], ticket['time']

			if ticket['time'] is not None:
				if total_time is None:
					total_time = ticket['time']
				else:
					total_time += ticket['time']

		if debug:
			print 'total_time:',total_time

		return total_time

	# format a tenrox comment based on a ticket dict
	#
	# ticket: the ticket dict
	#
	# return: the tenrox comment ([LBR-12345|01:30:45])
	def _get_tenrox_comment(self,ticket):

		comment = '[{0}|{1}]'

		return comment.format(ticket['ticket_id'],ticket['time'])

	# Build a summary per project from a list of ticket dicts
	#
	# tickets: ticket dicts
	#
	# returns: [{
	#    'project': 'LBR',
	#    'time': '01:30:35'
	# }]
	def _get_project_summary(self,tickets):

		projects = []

		for ticket in tickets:

			exists = self._get_from_dict(projects,'project',ticket['project'])

			if exists is None:
				p = {
					'project': ticket['project'],
					'time': ticket['time'],
					'tenrox_code': self._get_tenrox_code(ticket['project']),
					'tenrox_comment': self._get_tenrox_comment(ticket)
				}
				projects.append(p)
			else:
				p = exists
				p['time'] += ticket['time']
				p['tenrox_comment'] += self._get_tenrox_comment(ticket)

		return projects

	#
	# Public functions
	#

	# Fully parse an ActiviyStream from Jira
	#
	# username: Jira username
	# password: Jira password
	# day:      Day of the month (e.g. 26)
	# month:    Month of the year (e.g. 09)
	#
	# returns: {
	#     'tickets': tickets,
	#     'projects': projects
	# }
	def do_activity_stream(self, username, password, day, month):

		stream   = self._get_stream(username,password)
		tickets  = self._parse_stream(stream,day,month)
		projects = self._get_project_summary(tickets)

		return {
			'tickets': tickets,
			'projects': projects
		}


# application specific error thrown by the ActivityStream
class ActivityStreamError(Exception):

	ERROR_CODES = {
		'DEFAULT': 'An error has occurred with the ActivityStream',
		'BAD_USER': 'Invalid username or password',
		'NO_ACTIVITIES': 'No activities were found on the date requested',
		'NO_TICKET_ID': 'Failed to find ticket_id in title',
		'BAD_TITLE': 'Failed to parse stream title',
		'BAD_TIME': 'Parsed time does not match validation'
	}

	# code should be a member of ERROR_CODES
	def __init__(self, code='DEFAULT', debug=None):

		self.code  = code
		self.debug = debug
		message    = self.ERROR_CODES[code]

		Exception.__init__(self, message)

