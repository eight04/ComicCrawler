#! python3

"""this is exh module for comiccrawler, support exhentai.org, g.e-hentai.org

"""

import re
from html import unescape

from ..core import Episode

header = {}
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
	cookie = []
	cookie.append("ipb_member_id=" + config["ipb_member_id"])
	cookie.append("ipb_pass_hash=" + config["ipb_pass_hash"])
	header["Cookie"] = ";".join(cookie)

def gettitle(html, url):
	t = re.findall("<h1 id=\"g(j|n)\">(.+?)</h1>", html)
	t = t[-1][1]
	
	return unescape(t)
	
def getepisodelist(html, url):
	title = "image"
	url = re.search("href=\"([^\"]+?-1)\"", html).group(1)
	e = Episode(title, url)
	return [e]

nl = 0
def getimgurl(html, url, page):
	global nl
	
	i = re.search("<img id=\"img\" src=\"(.+?)\"", html)
	i = unescape(i.group(1))
	nl = re.search("nl\((\d+)\)", html).group(1)
	
	# bandwith limit
	if re.search("509s?\.gif", i) or re.search("403s?\.gif", i):
		raise Exception("Bandwidth limit exceeded!")
		
	return i

def errorhandler(er, ep):
	np = ep.current_url.split("?")[0] + "?nl={}".format(nl)
	if ep.current_url == np:
		ep.current_url = np.split("?")[0]
	else:
		ep.current_url = np

def getnextpageurl(html, url, pagenumber):
	r = re.search("href=\"([^\"]+?-{})\"".format(pagenumber+1), html)
	if r is None:
		return ""
	else:
		return r.group(1)
		