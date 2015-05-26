#! python3

"""this is ck101 module for comiccrawler

Ex:
	http://comic.ck101.com/comic/8373
	
"""

import re

from ..safeprint import safeprint
from ..core import Episode, grabhtml
from ..error import SkipEpisodeError


domain = ["comic.ck101.com"]
name = "卡提諾"

def gettitle(html, url):
	return re.search("<h1 itemprop=\"name\">(.+?)</h1>", html).group(1)
	
def getepisodelist(html, url):
	s = []
	base = re.search("(https?://[^/]+)", url).group(1)
	while True:
		for m in re.finditer("<a onclick=\"_gaq.push\(\['_trackEvent', '詳情頁-lists','[^']+','[^']+'\]\);\" target=\"_blank\" href=\"([^\"]+)\" title=\"[^\"]+\">(.+?)</a>", html, re.M):
			url, title = m
			e = Episode(m.group(2), base + m.group(1))
			s.append(e)
			
		un = re.search("ref=\"([^\"]+?)\" title='下一頁'", html)
		if un is None:
			break
		safeprint(base + un.group(1))
		html = grabhtml(base + un.group(1))
	return s[::-1]

def getimgurl(html, url, page):
	"""
	Since ck101 has lots of bugs, something like this: 
		http://comic.ck101.com/vols/9206635/1
	or this:
		http://comic.ck101.com/vols/9285077/15
	we raise SkipEpisodeError if getting losted page
	"""
	try:
		pic = re.search("'defualtPagePic' src=\"(.+?)\"", html).group(1)
		return pic
	except Exception:
		ex = re.search("李組長眉頭一皺，快翻下一頁→", html)
		if ex:
			raise SkipEpisodeError
		else:
			raise
			
def getnextpageurl(html, url, page):
	base = re.search("(https?://[^/]+)", url).group(1)
	r = re.search("<a href=\"(.+?)\" class=\"nextPageButton\" title=\"下一頁\">", html)
	if r is None:
		return ""
	return base + r.group(1)
