from activity_stream import ActivityStream
from tempo           import Tempo
from jtime_error     import jTimeError
from utils           import JTUtils
from shared.utils    import HTTPUtilsError
from datetime        import *
import ConfigParser

# Class to build a timesheet based on tickets recieved from activity_stream or tempo
class jTime():

	def __init__ (self, config):

		self.config = config
		self.act    = ActivityStream(config)
		self.tempo  = Tempo(config)
		self.utils  = JTUtils()

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

			exists = self.utils.get_from_dict(projects,'project',ticket['project'])

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

		hour   = int(spl[0])
		minute = int(spl[1])
		second = int(spl[2])
		up_from_zero = True

		# first round the minutes up or down as appropriate
		if second > 30:
			minute += 1

		if hour > 0:
			up_from_zero = False

		minute = self._round_tenrox_minutes(minute,up_from_zero)
		
		# round up the hour if necessary
		if minute == 1.0:
			hour += 1
			minute = 0.0

		return hour + minute

	# Round (convert) standard clock minutes into tenrox values
	#
	# minutes:      amount of minutes we're rounding
	# up_from_zero: do we want to round 0.00 to 0.25?
	#
	# return: tenrox minutes (15 minutes = 0.25)
	def _round_tenrox_minutes(self,minutes,up_from_zero=True):

		# return 0 minutes if not rounding 0 up
		if not up_from_zero and minutes <= 7:
			return 0

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
	def do(self, username, password, date):

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

		projects = self._get_project_summary(tickets)
		summary  = self._get_total_summary(projects)

		return {
			'tickets': tickets,
			'projects': projects,
			'summary': summary
		}

