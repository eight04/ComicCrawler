#! python3

"""this is danbooru module for comiccrawler

Ex:
	https://danbooru.donmai.us/posts?tags=fault!!

"""

import re
import comiccrawler as cc
from html import unescape
from safeprint import safeprint

domain = ["danbooru.donmai.us"]
name = "Danbooru"
noepfolder = True
header = {}

def gettitle(html, **kw):
	title = re.search(r"<title>(.+?)</title>", html, flags=re.DOTALL).group(1)
	return title.strip()
	
def getepisodelist(html, url=""):
	s = []
	base = re.search("(https?://[^/]+)", url).group(1)
	while True:
		for match in re.finditer(r'href="(/posts/(\d+)[^"]*)"', html):
			u = match.group(1)
			title = match.group(2)
			e = cc.Episode()
			e.title = title
			e.firstpageurl = base + u
			s.append(e)
			# safeprint(u)
			
		u = re.search(r'"([^"]+)" rel="next"', html)
		if not u:
			break
		u = base + unescape(u.group(1))
		safeprint(u)
		html = cc.grabhtml(u)
			
	return s[::-1]

def getimgurls(html, url=""):
	# with open("{}.log".format(cc.safefilepath(url)), "w", encoding="utf-8") as file:
		# file.write(html)
	base = re.search(r"(https?://[^/]+)", url).group(1)
	pos = re.search(r"image-container", html).start()
	imgRe = re.compile(r'data-file-url="([^"]+)"')
	img = imgRe.search(html, pos).group(1)
	return [base + img]

def errorhandler(er, ep):
	pass
	
def getnextpageurl(pagenumber, html, url=""):
	pass
	