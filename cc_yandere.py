#! python3

"""this is yandere module for comiccrawler

Ex:
	https://yande.re/post?tags=koikishi_purely_kiss

"""

import re
import comiccrawler as cc
from html import unescape
from safeprint import safeprint

domain = ["yande.re"]
name = "yande.re"
noepfolder = True
header = {}

def gettitle(html, **kw):
	title = re.search(r"<title>/(.+?)</title>", html, flags=re.DOTALL).group(1)
	return title.strip("/")
	
def getepisodelist(html, url=""):
	s = []
	base = re.search("(https?://[^/]+)", url).group(1)
	while True:
		for match in re.finditer(r'href="(/post/show/(\d+)[^"]*)"', html):
			u = match.group(1)
			title = match.group(2)
			e = cc.Episode()
			e.title = title
			e.firstpageurl = base + u
			s.append(e)
			
		u = re.search(r'rel="next" href="([^"]+)"', html)
		if not u:
			break
		u = base + unescape(u.group(1))
		safeprint(u)
		html = cc.grabhtml(u)
			
	return s[::-1]

def getimgurls(html, url=""):
	# base = re.search(r"(https?://[^/]+)", url).group(1)
	
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

def errorhandler(er, ep):
	pass
	
def getnextpageurl(pagenumber, html, url=""):
	pass
	