from activity_stream import *
from ConfigParser    import SafeConfigParser
from datetime        import datetime
import web, sys

# globals
render = None
config = None
act    = None

class index:

	def GET(self):

		data = web.input()
		msg = None

		try:
			msg = data.msg
		except AttributeError:
			pass

		if msg is not None:
			msg = ActivityStreamError.ERROR_CODES[msg]

		return render.index(
			config.get('app','elevenrox_url'),
			msg
		)

class jtime:

	def POST(self):

		global config, act

		data = web.input()

		try:
			as_rtn = self.do_activity_stream(data)
		except ActivityStreamError as e:
			print e.message
			if e.code == 'BAD_J_USER' or e.code == 'NO_ACTIVITIES':
				web.seeother('/?msg=' + e.code)
				return
			raise e

		return render.jtime(
			data.date,
			as_rtn['tickets'],
			as_rtn['projects'],
			as_rtn['summary'],
			data.t_username,
			data.t_password,
			data.tenrox_token,
			config.get('app','elevenrox_url')
		)

	def do_activity_stream(self,data):

		global config

		# how many times should we retry when Jira doesn't return anything?
		no_act_retries = config.getint('app','no_act_retries')

		while no_act_retries >= 0:

			try:
				d = data.date.rsplit('/')
				date = datetime(int(d[2]),int(d[1]),int(d[0]))

				return act.do_activity_stream(
					data.j_username,
					data.j_password,
					date
				)
			except ActivityStreamError as e:
				if e.code != 'NO_ACTIVITIES':
					raise e

			print 'retrying for no activities error',no_act_retries,'retries remaining'

			no_act_retries -= 1


		# if we've got this far, we should raise NO_ACTIVITIES
		raise ActivityStreamError('NO_ACTIVITIES')


class Server():

	def __init__ (self):

		global config, render, act

		# read the conf
		config = SafeConfigParser()
		config.read('activity_stream.cfg')
		config.read('password.cfg')

		# grab the port and spoof command args
		port = config.get('app','port')
		sys.argv.append(port)

		# set up the urls we're going to serve
		self._set_urls()

		render = web.template.render('html/')

		# spin up an instance of activity stream
		act = ActivityStream(config)

	def _set_urls(self):

		self.urls = (
			'/', 'index',
			'/doJTime', 'jtime'
		)

	def run(self):

		self.app = web.application(self.urls, globals())
		self.app.run()


if __name__ == "__main__":

	server = Server()
	server.run()
