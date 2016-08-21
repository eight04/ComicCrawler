#! python3

"""this is hhxiee module for comiccrawler

Ex:
	http://www.hhxiee.com/comic/1827966/
	
"""

import re
import execjs
import json

from urllib.parse import urljoin, urlparse

from ..core import Episode, grabhtml

domain = ["www.hhxiee.com"]
name = "汗汗"

def get_title(html, url):
	return re.search("<title>([^<]+)", html).group(1).partition(",")[0]
	
def get_episodes(html, url):
	eps = []
	
	for match in re.finditer(r"href=(/xiee/[^>\s]+).+?>([^<]+)", html):
		ep_url, title = match.groups()
		eps.append(Episode(title, urljoin(url, ep_url)))
	return eps[::-1]
			
def get_images(html, url):
	# piclisturl
	PicListUrl = re.search("var PicListUrl = .+?;", html).group()
	js_url = urljoin(url, "/hh/8.js")
	js = grabhtml(js_url)
	ctx = execjs.compile(
		"""
		var location = {
			href: """ + json.dumps(url) + """,
			hostname: """ + json.dumps(urlparse(url).hostname) + """
		};
		var document = {
			location: location
		};
		var window = {
			document: document
		};
		""" + PicListUrl + js
	)
	server, imgs = ctx.eval("[ServerList[server-1], arrPicListUrl]")
	return [server + i for i in imgs]
			