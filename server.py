from jtime        import jTime
from jtime_error  import jTimeError
from ConfigParser import SafeConfigParser
from datetime     import datetime
import web, sys

# globals
render = None
config = None
jt     = None

class index:

	def GET(self):

		data = web.input()
		msg = None

		try:
			msg = data.msg
		except AttributeError:
			pass

		if msg is not None:
			msg = jTimeError.ERROR_CODES[msg]

		return render.index(
			config.get('app','elevenrox_url'),
			msg
		)

class jtime:

	def POST(self):

		global config, act

		data = web.input()

		try:
			rtn = self.do_jtime(data)
		except jTimeError as e:
			print e.message
			web.seeother('/jTime?msg=' + e.code)
			return

		return render.jtime(
			data.date,
			rtn['tickets'],
			rtn['projects'],
			rtn['summary'],
			data.t_username,
			data.t_password,
			data.tenrox_token,
			config.get('app','elevenrox_url'),
			config.get('jira','jira_url')
		)

	def do_jtime(self,data):

		global jt

		d = data.date.rsplit('/')
		date = datetime(int(d[2]),int(d[1]),int(d[0]))

		return jt.do(data.j_username,data.j_password,date)

class Server():

	def __init__ (self):

		global config, render, jt

		# read the conf
		config = SafeConfigParser()
		config.read('jtime.cfg')
		config.read('password.cfg')

		# grab the port and spoof command args
		port = config.get('app','port')
		sys.argv.append(port)

		# set up the urls we're going to serve
		self._set_urls()

		render = web.template.render('html/')

		# spin up an instance of jTime
		jt = jTime(config)

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
