#! python3

import re
from html import unescape

from ..core import Episode, grabhtml
from ..safeprint import safeprint

header = {}
domain = ["chan.sankakucomplex.com"]
name = "Sankaku"
noepfolder = True
config = {
	"cf_clearance": "請輸入Cookie中的cf_clearance"
}

def loadconfig():
	header["Cookie"] = "cf_clearance=" + config["cf_clearance"]

def gettitle(html, url):
	title = re.search(r"<title>/?(.+?) \|", html).group(1)
	return "[sankaku] " + title
	
def getepisodelist(html, url):
	s = []
	base = re.search("(https?://[^/]+)", url).group(1)
	while True:
		ms = re.findall(r'href="(/(?:[^/]*/)?post/show/(\d+))"', html)
		
		for m in ms:
			url, pid = m
			
			e = Episode()
			e.title = pid
			e.firstpageurl = base + url
			s.append(e)

		m = re.search('next-page-url="([^"]+)"', html)
		if not m:
			break
		u = unescape(m.group(1))
		safeprint(base + u)
		html = grabhtml(base + u, header)
	return s[::-1]

def getimgurls(html, url):
	u = re.search('href="([^"]+)" id=highres', html)
	if not u:
		u = re.search('embed src="([^"]+)"', html)
	return ["https:" + u.group(1)]
	