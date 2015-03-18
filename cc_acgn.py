#! python3

"""this is acgn module for comiccrawler

Ex:
	http://comic.acgn.cc/manhua-murcielago.htm

"""

import re, execjs
from comiccrawler import Episode, extend, grabhtml, LastPageError, SkipEpisodeError
from safeprint import safeprint
from html import unescape

header = {
	# "Referer": "http://www.pixiv.net/member_illust.php"
}
domain = ["comic.acgn.cc"]
name = "ACGN.cc"
# noepfolder = True

# def loadconfig(config):
	# if name not in config:
		# config[name] = {}
	# extend(config[name], {
		# "SESSID": "請輸入Cookie中的PHPSESSID"
	# })
	# header["Cookie"] = "PHPSESSID=" + config[name]["SESSID"]

def gettitle(html, **kw):
	title = re.search(r"h3><a[^>]+>([^<]+)", html).group(1)
	return unescape(title)
	
def getepisodelist(html, url=""):
	s = []
	# root = re.search("https?://[^/]+", url).group()
	# base = re.search("https?://[^?]+", url).group()
	cwd = re.search("https?://[^?]+/", url).group()
	
	for match in re.finditer(r'a href="(view-[^"]+)"[^>]*>([^<]+)<', html):
		u = match.group(1)
		title = match.group(2)
		# safeprint(u)
		e = Episode()
		e.title = unescape(title)
		e.firstpageurl = cwd + u
		s.append(e)
		
	return s[::-1]

def getimgurls(html, url=""):
	s = []
	for match in re.finditer(r'_src="([^"]+)"', html):
		u = match.group(1)
		s.append(u)
	return s

def errorhandler(er, ep):
	pass

def getnextpageurl(pagenumber, html, url=""):
	pass
	