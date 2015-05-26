#! python3

"""this is konachan module for comiccrawler

Ex:
	http://konachan.com/pool/show/218

"""

import re
from html import unescape

from ..core import Episode, grabhtml
from ..safeprint import safeprint

domain = ["konachan.com"]
name = "Konachan"
noepfolder = True

def gettitle(html, url):
	title = re.search(r"<title>/?(.+?) \|", html).group(1)
	return "[konachan] " + title
	
def getepisodelist(html, url):
	s = []
	base = re.search("(https?://[^/]+)", url).group(1)
	while True:
		ms = re.findall('<a class="thumb" href="([^"]+)"', html)
		for m in ms:
			url = m
			uid = re.search(r"show/(\d+)", url).group(1)
			e = Episode(uid, base + url)
			s.append(e)
			
		un = re.search('<a class="next_page" rel="next" href="([^"]+)">', html)
		if un is None:
			break
		u = unescape(un.group(1))
		safeprint(base + u)
		html = grabhtml(base + u)
	return s[::-1]

def getimgurls(html, url):
	img = re.search('href="([^"]+)" id="highres"', html).group(1)
	return [img]
