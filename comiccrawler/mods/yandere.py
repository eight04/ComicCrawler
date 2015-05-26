#! python3

"""this is yandere module for comiccrawler

Ex:
	https://yande.re/post?tags=koikishi_purely_kiss

"""

import re
from html import unescape

from ..core import Episode, grabhtml
from ..safeprint import safeprint

domain = ["yande.re"]
name = "yande.re"
noepfolder = True

def gettitle(html, url):
	title = re.search(r"<title>/(.+?)</title>", html, flags=re.DOTALL).group(1)
	return title.strip("/")
	
def getepisodelist(html, url):
	s = []
	base = re.search("(https?://[^/]+)", url).group(1)
	while True:
		for match in re.finditer(r'href="(/post/show/(\d+)[^"]*)"', html):
			u = match.group(1)
			title = match.group(2)
			e = Episode(title, base + u)
			s.append(e)
			
		u = re.search(r'rel="next" href="([^"]+)"', html)
		if not u:
			break
		u = base + unescape(u.group(1))
		safeprint(u)
		html = grabhtml(u)
			
	return s[::-1]

def getimgurls(html, url):
	
	# Original
	img = re.search(
		r'class="original-file-unchanged"[^>]*?href="([^"]+)"',
		html
	)
	
	# Larger version
	if not img:
		img = re.search(r'id="highres" href="([^"]+)"', html)
		
	img = img.group(1)

	return [img]
