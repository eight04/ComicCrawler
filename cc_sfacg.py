#! python3

"""this is sfacg module for comiccrawler

Ex:
	http://comic.sfacg.com/HTML/PFSLL/

"""

import re
import comiccrawler
from safeprint import safeprint

header = {}
domain = ["comic.sfacg.com"]
name = "SF"

def gettitle(html, **kw):
	html = html.replace("\n","")
	t = re.search("<title>(.+?)</title>", html).group(1)
	return t.split(",")[0]
	
def getepisodelist(html, url=""):
	# html = html.replace("\n","")
	ms = re.findall("<li><a href=\"(.+?)\" target=\"_blank\">(.+?)</a></li>", html, re.M)
	base = re.search("(https?://[^/]+)", url).group(1)
	safeprint(ms)
	s = []
	for m in ms:
		url, title = m
		e = comiccrawler.Episode()
		title = re.sub("<.+?>","",title)
		e.title = title
		e.firstpageurl = base + url
		s.append(e)
	return s[::-1]

	
def getimgurls(html, page=0, url=""):

	js = re.search("src=\"(/Utility/.+?\.js)\"", html).group(1)
	base = re.search("(https?://[^/]+)", url).group(1)
	
	htmljs = comiccrawler.grabhtml(base + js)	
	host = "http://coldpic.sfacg.com"
	pics = re.findall("picAy\[\d+\] = \"(.+?)\"", htmljs)
	return [base + pic for pic in pics]
	

def errorhandler(er, ep):
	pass