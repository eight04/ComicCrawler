#! python3

"""this is ck101 module for comiccrawler

Ex:
	http://comic.ck101.com/comic/8373
	
"""

import re
import comiccrawler
from safeprint import safeprint

header = {"User-Agent": "Mozilla/5.0 (Windows NT 6.1; WOW64; rv:23.0) Gecko/20100101 Firefox/23.0"}
domain = ["comic.ck101.com"]
name = "卡提諾"

def gettitle(html, **kw):
	# html = html.replace("\n","")
	t = re.search("<h1 itemprop=\"name\">(.+?)</h1>", html).group(1)
	return t
	
def getepisodelist(html, url=""):
	# html = html.replace("\n","")
	# print("test")
	s = []
	base = re.search("(https?://[^/]+)", url).group(1)
	while True:
		ms = re.findall("<a onclick=\"_gaq.push\(\['_trackEvent', '詳情頁-lists','[^']+','[^']+'\]\);\" target=\"_blank\" href=\"([^\"]+)\" title=\"[^\"]+\">(.+?)</a>", html, re.M)
		safeprint(str(ms))
		
		for m in ms:
			url, title = m
			e = comiccrawler.Episode()
			# title = re.sub("<.+?>","",title)
			e.title = title
			e.firstpageurl = base + url
			s.append(e)
			
		un = re.search("ref=\"([^\"]+?)\" title='下一頁'", html)
		if un is None:
			break
		safeprint(base + un.group(1))
		html = comiccrawler.grabhtml(base + un.group(1), hd=header)
	return s[::-1]

def getimgurl(html, page=0, url=""):
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
	except Exception as er:
		ex = re.search("李組長眉頭一皺，快翻下一頁→", html)
		if ex:
			raise LostPageError
		else:
			raise er
			
class LostPageError(Exception): pass

def errorhandler(er, ep):
	if type(er) == LostPageError:
		raise comiccrawler.SkipEpisodeError

def getnextpageurl(pagenumber, html, url=""):
	base = re.search("(https?://[^/]+)", url).group(1)
	r = re.search("<a href=\"(.+?)\" class=\"nextPageButton\" title=\"下一頁\">", html)
	if r is None:
		return ""
	return base + r.group(1)
