#! python3

"""this is exh module for comiccrawler, support exhentai.org, g.e-hentai.org

"""

import re
from html import unescape
from urllib.parse import urljoin

from ..core import Episode

cookie = {}
domain = ["exhentai.org", "g.e-hentai.org"]
name = "e紳士"
noepfolder = True
rest = 5
config = {
	"ipb_member_id": "請輸入Cookie中的ipb_member_id",
	"ipb_pass_hash": "請輸入Cookie中的ipb_pass_hash"
}

class BandwidthLimitError(Exception): pass

def loadconfig():
	cookie.update(config)

def gettitle(html, url):
	t = re.findall("<h1 id=\"g(j|n)\">(.+?)</h1>", html)
	t = t[-1][1]

	return unescape(t)

def getepisodelist(html, url):
	url = re.search(r'href="([^\"]+?/s/\w+/\w+-1)"', html).group(1)
	e = Episode("image", url)
	return [e]

nl = ""
def getimgurl(html, url, page):
	global nl
	i = re.search("<img id=\"img\" src=\"(.+?)\"", html)
	i = unescape(i.group(1))
	nl = re.search("nl\('([^)]+)'\)", html).group(1)

	# bandwith limit
	if re.search("509s?\.gif", i) or re.search("403s?\.gif", i):
		raise Exception("Bandwidth limit exceeded!")

	return i

def errorhandler(er, ep):
	global nl
	url = urljoin(ep.current_url, "?nl=" + nl)
	if ep.current_url == url:
		ep.current_url = url.split("?")[0]
	else:
		ep.current_url = url

def getnextpageurl(html, url, pagenumber):
	r = re.search("href=\"([^\"]+?-{})\"".format(pagenumber+1), html)
	if r is None:
		return ""
	else:
		return r.group(1)
