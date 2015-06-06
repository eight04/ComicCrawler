#! python3

"""this is yandere module for comiccrawler

Ex:
	https://yande.re/post?tags=koikishi_purely_kiss

"""

import re, execjs
from comiccrawler import Episode, grabhtml
from html import unescape
from safeprint import safeprint
from functools import partial

domain = ["iibq.com"]
name = "精明眼"
noepfolder = False
header = {}

def gettitle(html, **kw):
	title = re.search(r"<h1[^>]*>(.+?)</h1>", html, re.DOTALL).group(1)
	return title.strip()
	
def getepisodelist(html, url=""):
	s = []
	html = html[html.index('<div class="cVol">'):]
	base = re.search("(https?://[^/]+)", url).group(1)
	for match in re.finditer(r"href='(http://www\.iibq\.com/comic/\d+/viewcomic\d+/)'>([^<]+)", html):
		u, title = match.groups()
		u = match.group(1)
		title = match.group(2)
		e = Episode()
		e.title = title
		e.firstpageurl = u
		s.append(e)
			
	return s[::-1]

def getimgurls(html, url=""):
	sFiles = re.search('sFiles="([^"]+)"').group(1)
	sPath = re.search('sPath="([^"]+)"').group(1)
	
	viewhtm = grabhtml("http://www.iibq.com/script/viewhtm.js")
	
	unsuan = partial(
		execjs.compile(
			re.search('window["\x65\x76\x61\x6c"](.+?)var cuImg', viewhtm, re.DOTALL).group(1).replace("location.hostname", "'www.iibq.com'")
		).call,
		"unsuan"
	)
	
	arrFiles = unsuan(sFiles).split("|")
	
	ds = grabhtml("http://www.iibq.com/script/ds.js")
	
	SLUrl = re.search('sDS = "([^"]+)"', ds).group(1).split("^")[0].split("|")[1]
	
	return [SLUrl + sPath + f for f in arrFiles]

def errorhandler(er, ep):
	pass
	
def getnextpageurl(pagenumber, html, url=""):
	pass
	