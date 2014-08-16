#! python3

import re
from html import unescape
from comiccrawler import Episode, grabhtml
from safeprint import safeprint

header = {
	"User-Agent": "Mozilla/5.0 (Windows NT 6.1; WOW64; rv:23.0) Gecko/20100101 Firefox/23.0"
}
domain = ["chan.sankakucomplex.com"]
name = "Sankaku"
noepfolder = True

def gettitle(html, **kw):
	title = re.search(r"<title>/?(.+?) \|", html).group(1)
	return "[sankaku] " + title
	
def getepisodelist(html, url="", **kw):
	s = []
	base = re.search("(https?://[^/]+)", url).group(1)
	while True:
		ms = re.findall(r'href="(/post/show/(\d+))"', html)
		
		for m in ms:
			url, pid = m
			
			e = Episode()
			e.title = pid
			e.firstpageurl = base + url
			s.append(e)

		m = re.search('next-page-url="([^"]+)"', html)
		if not m:
			break
		u = unescape(m.group(1))
		safeprint(base + u)
		html = grabhtml(base + u, header)
	return s[::-1]

def getimgurls(html, url=""):
	u = re.search('href="([^"]+)" id=highres', html)
	if not u:
		u = re.search('embed src="([^"]+)"', html)
	return ["https:" + u.group(1)]
	
def errorhandler(er, ep):
	pass
	
def getnextpageurl(pagenumber, html):
	pass
