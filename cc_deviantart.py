#! python3

"""this is deviant module for comiccrawler, support deviantart.com

"""

import re
import comiccrawler
from safeprint import safeprint
from html import unescape

header = {
	"User-Agent": "Mozilla/5.0 (Windows NT 6.1; WOW64; rv:23.0) "
			"Gecko/20100101 Firefox/23.0"
}
domain = ["deviantart.com"]
name = "dA"
noepfolder = True

def loadconfig(config):
	if name not in config:
		config[name] = {}
	config = config[name]
	cookie = []
	if "auth" in config:
		cookie.append("auth=" + unescape(config["auth"]))
	else:
		config["auth"] = "請輸入Cookie中的auth"
	if "userinfo" in config:
		cookie.append("userinfo=" + unescape(config["userinfo"]))
	else:
		config["userinfo"] = "請輸入Cookie中的userinfo"
	header["Cookie"] = ";".join(cookie)

def gettitle(html, **kw):
	t = re.search("<title>(.+?)</title>", html).group(1)
	# t = t[0][0]
	return t.replace("&#039;", "'")
	
def getepisodelist(html, url):
	base = re.search("(https?://[^/]+)", url).group(1)
	s = []
	while True:
		safeprint(url)
		startpos = html.index('id="gmi-ResourceStream"')
		ex = re.compile('<a class="thumb[^"]*?" href="({}/art/.+?)" title="(.+?)"'.format(base))
		r = ex.findall(html, startpos)
		for m in r:
			id = re.search("\d+$", m[0]).group()
			title = m[1].rpartition(" by ")[0]
			# WTF r u doing deviantArt?
			title = unescape(unescape(title))
			
			e = comiccrawler.Episode()
			e.firstpageurl = m[0]
			e.title = "{} - {}".format(id, title)
			s.append(e)
			
		next = re.search('id="gmi-GPageButton"[^>]+?href="([^"]+?)"><span>Next</span>', html)
		if not next:
			break
		url = base + next.group(1).replace("&amp;", "&")
		html = comiccrawler.grabhtml(url, header)
		
	return s[::-1]


def getimgurls(html, **kw):
	loggedin = re.search('"loggedIn":true', html)
	if not loggedin:
		safeprint("Warning! You didn't log in.")
	html = html.replace("\n", "")
	try:
		i = re.search('dev-page-download"\s+href="([^"]+)"',html).group(1)
		return [unescape(i)]
	except Exception:
		pass
	i = re.search('<img[^>]+src="([^"]+)"[^>]+class="dev-content-full">', html).group(1)
	return [i]

def errorhandler(er, ep):
	pass
	
def getnextpageurl(pagenumber, html, **kw):
	pass
		