#! python3

"""this is dm5 module for comiccrawler

Ex:
	http://www.dm5.com/manhua-yaojingdeweiba/
	
"""

import re
import execjs
import comiccrawler
from safeprint import safeprint

header = {
	"User-Agent": "Mozilla/5.0 (Windows NT 6.1; WOW64; rv:23.0) Gecko/20100101 Firefox/23.0",
	"Cookie": "isAdult=1"
}
domain = ["www.dm5.com"]
name = "動漫屋"

def gettitle(html, **kw):
	# html = html.replace("\n","")
	t = re.search("class=\"inbt_title_h2\">([^<]+)</h1>", html).group(1)
	return t
	
def getepisodelist(html, url=""):
	# html = html.replace("\n","")
	# print("test")
	s = []
	base = re.search("(https?://[^/]+)", url).group(1)
	html = html[html.index("cbc_1"):]
	
	ms = re.findall("class=\"tg\" href=\"([^\"]+)\" title=\"([^\"]+)\"", html)
	# safeprint(str(ms))
	
	for m in ms:
		url, title = m
		e = comiccrawler.Episode()
		# title = re.sub("<.+?>","",title)
		e.title = title
		e.firstpageurl = base + url
		s.append(e)
		
	return s[::-1]

def getimgurls(html, page=0, url=""):
	header["Referer"] = url
	pages = re.search("DM5_IMAGE_COUNT=(\d+);", html).group(1)
	cid = re.search("DM5_CID=(\d+);", html).group(1)
	s = []
	for p in range(1, int(pages)+1):
		ot = comiccrawler.grabhtml("http://www.dm5.com/m156516/chapterimagefun.ashx?cid={}&page={}&language=1&key=".format(cid, p), hd=header)
		s.append(execjs.eval(ot)[0])
	return s

def errorhandler(er, ep):
	pass

def getnextpageurl(pagenumber, html, url=""):
	pass