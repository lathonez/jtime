from activity_stream import ActivityStream
from tempo           import Tempo
from jtime_error     import jTimeError
from utils           import *
from shared.utils    import HTTPUtils, HTTPUtilsError
from datetime        import *

# Class to build a timesheet based on tickets recieved from activity_stream or tempo
class jTime():

	def __init__ (self, config):

		self.config = config
		self.act    = ActivityStream(config)
		self.tempo  = Tempo(config)
		self.utils  = JTUtils()
		self.jira   = JiraUtils(config,HTTPUtils(config))

	# Build a summary per assignment from a list of ticket dicts
	#
	# tickets: ticket dicts
	#
	# returns: [{
	#    'assignment': 'LBR300 Investigation',
	#    'time': '01:30:35'
	# }]
	def _get_assignments(self,tickets):

		assignments = []

		for ticket in tickets:

			# do we already have this assignment?
			exists = self.utils.get_from_dict(assignments,'assignment',ticket['assignment_name'])

			if exists is None:
				a = {
					'assignment': ticket['assignment_name'],
					'project': ticket['project'],
					'time': ticket['time'],
					'tenrox_comment': self._get_tenrox_comment(ticket)
				}
				assignments.append(a)
			else:
				a = exists
				a['time'] += ticket['time']
				a['tenrox_comment'] += self._get_tenrox_comment(ticket)

		# round up the tenrox time in each project
		for assignment in assignments:
			assignment['tenrox_time'] = self._round_tenrox_time(assignment['time'])

		return assignments

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

	# format a tenrox comment based on a ticket dict
	#
	# ticket: the ticket dict
	#
	# return: the tenrox comment ([LBR-12345|01:30:45])
	def _get_tenrox_comment(self,ticket):

		comment = '[{0}|{1}]'

		return comment.format(ticket['ticket_id'],ticket['time'])

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

	# get tickets, projects and a summary for a given date
	#
	# username:  jira username
	# password:  jira password
	# date:      datetime
	#
	# returns: {
	#     'tickets': tickets,
	#     'projects': projects,
	#     'summary': {total_time: '07:30:59', total_tenrox_time: '7.5'}
	# }
	def do(self, username, password, date, find_codes):

		tickets = None

		try:
			tickets  = self.tempo.get_tickets(username, password, date)
		except jTimeError as e:
			if e.code != 'NO_ACTIVITIES':
				raise e
		except HTTPUtilsError:
			raise jTimeError('HTTP_JIRA')

		# if we've got nothing from tempo, try the activity stream
		if tickets is None:
			no_act_retries = self.config.getint('activity_stream','no_act_retries')

			while no_act_retries >= 0:
				try:
					tickets = self.act.get_tickets(username, password, date)
					break
				except jTimeError as e:
					if e.code != 'NO_ACTIVITIES':
						raise e

				print 'retrying for no activities error',no_act_retries,'retries remaining'
				no_act_retries -= 1

			# if we've got this far with no tickets, we should raise NO_ACTIVITIES
			if tickets is None:
				raise jTimeError('NO_ACTIVITIES')

		# try to find the tenrox codes from Jira
		if find_codes:

			cookies = self.jira.login(username, password)

			for ticket in tickets:
				rtn = self.jira.get_tenrox_code_from_ticket(
					ticket['ticket_id'],cookies
				)
				ticket['assignment_name'] = rtn['tenrox_code']
				cookies                   = rtn['cookies']

		assignments = self._get_assignments(tickets)
		summary     = self._get_total_summary(assignments)

		return {
			'tickets': tickets,
			'assignments': assignments,
			'summary': summary
		}

