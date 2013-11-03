# Utility for parsing Jira HTML
#
from bs4 import BeautifulSoup
import re

# wrapper for BeautifulSoup with some helper fns for Jira
class JTHTMLUtils():

	# html - html string you want to use with this instance
	#        of the parser
	def __init__(self, html):

		self.html = html
		self.soup = BeautifulSoup(html)

	# check whether or not the user is logged in based on the response body
	def is_logged_in(self):

		# TODO - we could do more with this (the CAPTCHA)
		err_div = self.soup.find_all('div', class_='aui-message error')

		if not len(err_div):
			return True

		return False

