#! python3

"""this is konachan module for comiccrawler

Ex:
	http://konachan.com/pool/show/218

"""

import re
import comiccrawler
from html import unescape
from safeprint import safeprint

header = {
	"User-Agent": "Mozilla/5.0 (Windows NT 6.1; WOW64; rv:23.0) Gecko/20100101 Firefox/23.0"
}
domain = ["konachan.com"]
name = "Konachan"
noepfolder = True

def gettitle(html, **kw):
	title = re.search(r"<title>/?(.+?) \|", html).group(1)
	return "[konachan] " + title
	
def getepisodelist(html, url=""):
	s = []
	base = re.search("(https?://[^/]+)", url).group(1)
	while True:
		ms = re.findall('<a class="thumb" href="([^"]+)"', html)
		# safeprint(ms)
		for m in ms:
			url = m
			# print(url)
			uid = re.search(r"show/(\d+)", url).group(1)
			e = comiccrawler.Episode()
			e.title = uid
			e.firstpageurl = base + url
			s.append(e)
			
		un = re.search('<a class="next_page" rel="next" href="([^"]+)">', html)
		if un is None:
			break
		u = unescape(un.group(1))
		safeprint(base + u)
		html = comiccrawler.grabhtml(base + u, hd=header)
	# safeprint(s)
	return s[::-1]

def getimgurls(html, url=""):
	img = re.search('href="([^"]+)" id="highres"', html).group(1)
	return [img]

def errorhandler(er, ep):
	pass
	
def getnextpageurl(pagenumber, html, url=""):
	pass
	