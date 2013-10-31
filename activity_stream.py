from shared.utils import HTTPUtils
from time         import mktime
from datetime     import *
import feedparser, re, ConfigParser

# Class to obtain and parse an activity stream from Jira
class ActivityStream():

	def __init__ (self, config):

		self.config = config
		self.http_utils = HTTPUtils(self.config)
		self.debug = self.config.getboolean('app','debug')
		self.debug_stream = self.config.getboolean('app','debug_stream')
		self.relevant_terms = self.config.get('app','relevant_terms').rsplit('|')

	# get the activity stream for a given user
	#
	# username: Jira username
	# password: Jira password
	#
	# return: feedparsed activiy stream
	def _get_stream(self, username, password, date):

		# get the weird jira seconds to work with
		from_secs = self._get_jira_seconds(date)
		to_secs   = self._get_jira_seconds(date+timedelta(days=1))

		url     = self.config.get('app','base_url')
		auth    = self.config.get('app','auth_type')
		results = self.config.get('app','results')

		# the stream filters are passed through as two streams variables
		time_stream = 'update-date+BETWEEN+{0}+{1}'.format(from_secs,to_secs)
		user_stream = 'user+IS+{0}'.format(username)
		streams = '{0}&streams={1}'.format(user_stream,time_stream)

		print 'get_stream: Attempting to get stream for user',username

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
			if str(e).find('HTTP error code: 401'):
				raise ActivityStreamError('BAD_J_USER')
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
	#
	# return: list of ticket dicts
	def _parse_stream(self, stream):

		fn      = '_parse_stream:'
		entries = stream.entries
		tickets = []

		if not len(entries):
			raise ActivityStreamError('NO_ACTIVITIES')

		print fn,len(stream.entries),'events found in stream'

		# placeholders to sanity check the available time
		first_entry = None
		last_entry  = None

		prev_entry  = None
		prev_ticket = None

		for entry in entries:

			if self.debug_stream:
				print entry

			# only process stuff we care about
			if not self._check_entry_relevant(entry):
				continue

			# we use relevant placeholders only to check the total time
			if first_entry is None:
				first_entry = entry

			last_entry = entry

			try:
				# temp ticket to test with
				t = self._build_ticket_dict(entry)
			except ActivityStreamError as e:
				# we've got a random event like 'linked two tickets', ignore
				if e.code == 'NO_TICKET_ID':
					print fn,'skipping entry @',entry['published']
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
		avail = self._get_time_difference(first_entry,last_entry)
		print fn,'Time Available:',avail

		total_time = self._get_total_time(tickets)
		if total_time != avail:
			raise ActivityStreamError('BAD_TIME','total_time: {0}, avail: {1}'.format(total_time,avail))
		else:
			print fn,total_time,'accounted for'

		# sort the results
		tickets = sorted(tickets, key=lambda k: k['ticket_id'])

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

		td          = self._parse_title_detail(entry['title_detail']['value'])
		project     = td['project']
		ticket_id   = project + '-' + td['ticket_id']

		return {
			'project': project,
			'ticket_id': ticket_id,
			'time': timedelta()
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
		rexp      = '([A-Z][A-Z][A-Z]*)-([1-9][0-9]*)'
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
	# returns: tenrox project name (LBR300)
	def _get_tenrox_project_name(self, project):

		try:
			code = self.config.get('tenrox_project_names',project)
		except ConfigParser.NoOptionError:
			code = project + '300 Investigation'

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
	def _get_total_time(self,tickets):

		total_time = timedelta()

		for ticket in tickets:

			if self.debug:
				print ticket['ticket_id'], ticket['time']

			total_time += ticket['time']

		if self.debug:
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
					'tenrox_project_name': self._get_tenrox_project_name(ticket['project']),
					'tenrox_comment': self._get_tenrox_comment(ticket)
				}
				projects.append(p)
			else:
				p = exists
				p['time'] += ticket['time']
				p['tenrox_comment'] += self._get_tenrox_comment(ticket)

		# round up the tenrox time in each project
		for project in projects:
			project['tenrox_time'] = self._round_tenrox_time(project['time'])

		return projects

	# Round a datetime.timedelta object into tenrox time (4.25 instead of 04:15)
	#
	# time: timedelta obj
	#
	# return: rounded tenrox time (double)
	def _round_tenrox_time(self,time):

		spl = str(time).rsplit(':')

		hour = int(spl[0])
		minute = int(spl[1])
		second = int(spl[2])

		# first round the minutes up or down as appropriate
		if second > 30:
			minute += 1

		minute = self._round_tenrox_minutes(minute)
		
		# round up the hour if necessary
		if minute == 1.0:
			hour += 1
			minute = 0.0

		return hour + minute

	# Round (convert) standard clock minutes into tenrox values
	#
	# minutes: amount of minutes we're rounding
	#
	# return: tenrox minutes (15 minutes = 0.25)
	def _round_tenrox_minutes(self,minutes):

		# we always have at least 0.25
		if minutes <= 22:
			return 0.25
		elif minutes <= 37:
			return 0.5
		elif minutes <= 52:
			return 0.75

		return 1.0

	# Sum the total time from a list of projects
	#
	# projects: list of project dicts
	#
	# return {total_time: '07:30:59', total_tenrox_time: '7.5'}
	def _get_total_summary(self, projects):

		time = timedelta()
		tenrox_time = 0.0

		for project in projects:
			time += project['time']
			tenrox_time += project['tenrox_time']

		return {
			'time': time,
			'tenrox_time': tenrox_time
		}

	# Get time in seconds since the epoch to a specific date * 1000
	#
	# date: datetime object
	#
	# returns (see above)
	def _get_jira_seconds(self, date):

		return int(round(float(date.strftime('%s.%f'))*1000,0))


	# check to see whether we want to be counting this entry in our timesheet
	#
	# entry - entry object from stream.entries
	#
	# returns - True if we should be counting the entry, else false
	def _check_entry_relevant(self, entry):

		fn = '_check_entry_relevant:'

		# no tags implies a ticket field change (priority, team, IM, etc), we keep these
		if 'tags' not in entry:
			return True

		t = entry['tags'][0]
		term = t['term']

		if term in self.relevant_terms:
			return True

		if self.debug:
			print fn,'not relevant - ',entry['title'].encode('utf-8')

		return False

	#
	# Public functions
	#

	# Fully parse an ActiviyStream from Jira
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
	def do_activity_stream(self, username, password, date):

		stream   = self._get_stream(username,password,date)
		tickets  = self._parse_stream(stream)
		projects = self._get_project_summary(tickets)
		summary  = self._get_total_summary(projects)

		return {
			'tickets': tickets,
			'projects': projects,
			'summary': summary
		}


# application specific error thrown by the ActivityStream
class ActivityStreamError(Exception):

	ERROR_CODES = {
		'DEFAULT': 'An error has occurred with the ActivityStream',
		'BAD_J_USER': 'Invalid Jira username or password',
		'BAD_T_USER': 'Invalid Tenrox username or password',
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

