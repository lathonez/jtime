from jtime_error  import jTimeError
from utils        import *
from shared.utils import HTTPUtils
from time         import mktime
from datetime     import *
import feedparser, re, ConfigParser

# Class to obtain and parse an activity stream from Jira
class ActivityStream():

	def __init__ (self, config):

		self.config         = config
		self.http_utils     = HTTPUtils(self.config)
		self.debug          = self.config.getboolean('app','debug')
		self.debug_stream   = self.config.getboolean('activity_stream','debug_stream')
		self.relevant_terms = self.config.get('activity_stream','relevant_terms').rsplit('|')
		self.jira           = JiraUtils(self.config)
		self.utils          = JTUtils()

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

		url     = self.config.get('jira','jira_url') + '/activity'
		auth    = self.config.get('jira','auth_type')
		results = self.config.get('activity_stream','results')

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
				raise jTimeError('BAD_J_USER')
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
	def _get_tickets(self, stream):

		fn      = '_parse_stream:'
		entries = stream.entries
		tickets = []

		if not len(entries):
			raise jTimeError('NO_ACTIVITIES')

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
				t = self.jira.build_ticket_dict(
					self.jira.parse_ticket_id(entry['title_detail']['value'])
				)
			except jTimeError as e:
				# we've got a random event like 'linked two tickets', ignore
				if e.code == 'NO_TICKET_ID':
					print fn,'skipping entry @',entry['published']
					continue
				else:
					raise e

			exists = self.utils.get_from_dict(tickets,'ticket_id',t['ticket_id'])

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
			raise jTimeError('BAD_TIME','total_time: {0}, avail: {1}'.format(total_time,avail))
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

	# Parse a Jira activity stream, returning a list of ticket dicts
	#
	# username: Jira username
	# password: Jira password
	# date:     datetime obj
	#
	# returns: tickets
	def get_tickets(self, username, password, date):

		stream = self._get_stream(username,password,date)
		return self._get_tickets(stream)

