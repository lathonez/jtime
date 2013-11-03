# application specific error thrown by jTime
class jTimeError(Exception):

	ERROR_CODES = {
		'DEFAULT': 'An error has occurred with the ActivityStream',
		'BAD_J_USER': 'Invalid Jira username or password',
		'BAD_T_USER': 'Invalid Tenrox username or password',
		'NO_ACTIVITIES': 'No activities were found on the date requested',
		'NO_TICKET_ID': 'Failed to find ticket_id in title',
		'BAD_TITLE': 'Failed to parse stream title',
		'BAD_TIME': 'Parsed time does not match validation',
		'HTTP_ELEVENROX': 'HTTP error when communicating with elevenRox',
		'HTTP_JIRA': 'HTTP error when communicating with Jira',
		'TEMPO_PARSE': 'Failed to parse Tempo Timesheet',
		'UNKNOWN': 'An unknown error has occurred'
	}

	# code should be a member of ERROR_CODES
	def __init__(self, code='DEFAULT', debug=None):

		self.code  = code
		self.debug = debug
		message    = self.ERROR_CODES[code]

		Exception.__init__(self, message)
