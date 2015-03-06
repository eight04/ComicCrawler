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
	"Cookie": "isAdult=1"
}
domain = ["www.dm5.com", "tel.dm5.com"]
name = "動漫屋"

def gettitle(html, **kw):
	# html = html.replace("\n","")
	t = re.search("class=\"inbt_title_h2\">([^<]+)</h1>", html).group(1)
	return t
	
def getepisodelist(html, url=""):
	s = []
	base = re.search("(https?://[^/]+)", url).group(1)
	html = html[html.index("cbc_1"):]
	
	ms = re.findall("class=\"tg\" href=\"([^\"]+)\" title=\"([^\"]+)\"", html)
	
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
	key = re.search(r'id="dm5_key".+?<script[^>]+?>\s*eval(.+?)</script>', html, re.S)
	if key:
		key = execjs.eval(key.group(1)).split(";")[1]
		key = re.search(r"=(.+)$", key).group(1)
		key = execjs.eval(key)
	else:
		key = ""
		
	base = re.search(r"(^.+)/[^/]*$", url).group(1)
	pages = re.search("DM5_IMAGE_COUNT=(\d+);", html).group(1)
	cid = re.search("DM5_CID=(\d+);", html).group(1)
	s = []
	for p in range(1, int(pages)+1):
		# ot = comiccrawler.grabhtml("http://www.dm5.com/m156516/chapterimagefun.ashx?cid={}&page={}&language=1&key=".format(cid, p), hd=header)
		currentUrl = "{}/chapterfun.ashx?cid={}&page={}&language=1&key={}".format(base, cid, p, key)
		ot = comiccrawler.grabhtml(currentUrl, hd=header)
		
		#debug
		with open("{}-{}.log".format(cid, p), "w", encoding="utf-8") as file:
			file.write(ot)
		
		context = execjs.compile(ot)
		d = context.eval("typeof (hd_c) != 'undefined' && hd_c.length > 0 && typeof (isrev) == 'undefined' ? hd_c : d")
		s.append(d[0])
	return s

def errorhandler(er, ep):
	pass

def getnextpageurl(pagenumber, html, url=""):
	pass