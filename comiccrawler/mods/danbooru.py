#! python3

"""this is danbooru module for comiccrawler

Ex:
	https://danbooru.donmai.us/posts?tags=fault!!

"""

import re
from html import unescape
from urllib.parse import urljoin

from ..safeprint import safeprint
from ..core import Episode, grabhtml

domain = ["danbooru.donmai.us"]
name = "Danbooru"
noepfolder = True

def gettitle(html, url):
	title = re.search(r"<title>(.+?)</title>", html, re.DOTALL).group(1)
	return title.strip()

def getepisodelist(html, url, last_episode):
	s = []
	while True:
		for match in re.finditer(r'href="(/posts/(\d+)[^"]*)"', html):
			u = match.group(1)
			title = match.group(2)
			e = Episode(title, urljoin(url, u))
			s.append(e)

		u = (re.search(r'"([^"]+)" rel="next"', html) or
			re.search(r'<a rel="next" href="([^"]+)', html))

		if not u:
			break

		u = urljoin(url, unescape(u.group(1)))
		safeprint(u)
		html = grabhtml(u)

	return s[::-1]

def getimgurls(html, url):
	pos = re.search(r"image-container", html).start()
	img = re.compile(r'data-file-url="([^"]+)"').search(html, pos).group(1)
	return [urljoin(url, img)]
