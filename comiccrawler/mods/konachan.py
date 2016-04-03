#! python3

"""this is konachan module for comiccrawler

Ex:
	http://konachan.com/pool/show/218

"""

import re
from html import unescape

from ..core import Episode, grabhtml
from ..safeprint import safeprint
from ..error import SkipEpisodeError

domain = ["konachan.com"]
name = "Konachan"
noepfolder = True

def gettitle(html, url):
	title = re.search(r"<title>/?(.+?) \|", html).group(1)
	return "[konachan] " + title
	
def getepisodelist(html, url, last_episode):
	s = []
	base = re.search("(https?://[^/]+)", url).group(1)
	while True:
		for m in re.finditer('<a class="thumb" href="([^"]+)"', html):
			url = m.group(1)
			uid = re.search(r"show/(\d+)", url).group(1)
			e = Episode(uid, base + url)
			if last_episode and last_episode.url == e.url:
				return s[::-1]
			s.append(e)
			
		un = re.search('<a class="next_page" rel="next" href="([^"]+)">', html)
		if un is None:
			break
		u = unescape(un.group(1))
		safeprint(base + u)
		html = grabhtml(base + u)
	return s[::-1]

def getimgurls(html, url):
	try:
		img = re.search('href="([^"]+)" id="highres"', html).group(1)
	except AttributeError:
		if "This post was deleted" in html:
			raise SkipEpisodeError
		else:
			raise
	return [img]
