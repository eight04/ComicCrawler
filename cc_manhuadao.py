#! python3

"""this is manhuadao module for comiccrawler

Ex:
	(http://www.999comic.com/comic/3300/)
	http://www.manhuadao.com/book/wudaokuangzhishi/
	
"""

import re
import execjs
import comiccrawler as cc
from safeprint import safeprint

header = {}
domain = ["www.manhuadao.com"]
name = "漫畫島"

def gettitle(html, **kw):
	t = re.search(r'class="book-title">\s*<h1>([^<]*)', html).group(1)
	return t
	
def getepisodelist(html, url=""):
	s = []
	base, id = re.search(r"(https?://[^/]+)/book/([^/]+)", url).groups()
	
	for match in re.finditer(r'href="(/book/{}/[^"]+)" title="([^"]+)"'.format(id), html):
		url, title = match.groups()
	
		e = cc.Episode()
		e.title = title
		e.firstpageurl = base + url
		s.append(e)
		
	return s[::-1]

def getimgurls(html, page=0, url=""):
	base, protocol, id = re.search(r"((https?://)[^/]+)/book/([^/]+)", url).groups()
	
	core = re.search(r'src="(/scripts/core[^"]+)"', html).group(1)
	cInfo = re.search(r'cInfo = ({[^;]+});', html).group(1)
	
	coreJs = cc.grabhtml(base + core, header)
	pageConfig = re.search(r'pageConfig=({[^;]+})', coreJs).group(1)
	
	images = execjs.eval(cInfo)["fs"]
	host = execjs.eval(pageConfig)["host"]
	
	header["Referer"] = url
	
	return [protocol + host + image for image in images]

def errorhandler(er, ep):
	pass

def getnextpageurl(pagenumber, html, url=""):
	pass