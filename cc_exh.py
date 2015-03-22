#! python3

"""this is exh module for comiccrawler, support exhentai.org, g.e-hentai.org

"""

import re
from html import unescape
from comiccrawler import Episode

header = {}
domain = ["exhentai.org", "g.e-hentai.org"]
name = "e紳士"
noepfolder = True
rest = 5

class BandwidthLimitError(Exception): pass

def loadconfig(config):
	if name not in config:
		config[name] = {}
	config = config[name]
	cookie = []
	if "ipb_member_id" in config:
		cookie.append("ipb_member_id=" + config["ipb_member_id"])
	else:
		config["ipb_member_id"] = "請輸入Cookie中的ipb_member_id"
	if "ipb_pass_hash" in config:
		cookie.append("ipb_pass_hash=" + config["ipb_pass_hash"])
	else:
		config["ipb_pass_hash"] = "請輸入Cookie中的ipb_pass_hash"
	header["Cookie"] = ";".join(cookie)

def gettitle(html, **kw):
	t = re.findall("<h1 id=\"g(j|n)\">(.+?)</h1>", html)
	t = t[-1][1]
	
	return unescape(t)
	
def getepisodelist(html, **kw):
	e = Episode()
	e.title = "image"
	e.firstpageurl = re.search("href=\"([^\"]+?-1)\"", html).group(1)
	# e.totalpages = int(re.search("<td class=\"gdt2\">(\d+) @", html).group(1))
	return [e]

def getimgurl(html, **kw):
	i = re.search("<img id=\"img\" src=\"(.+?)\"", html)
	
	i = i.group(1).replace("&amp;","&")
	# bandwith limit
	if re.search("509s?\.gif",i) is not None or re.search("403s?\.gif",i) is not None:
		nl = re.search("nl\((\d+)\)", html).group(1)
		raise BandwidthLimitError(nl)
	return i

def errorhandler(er, ep):
	if type(er) is BandwidthLimitError:
		nl = er.args[0]
		np = ep.currentpageurl.split("?")[0] + "?nl={}".format(nl)
		if ep.currentpageurl == np:
			ep.currentpageurl = np.split("?")[0]
		else:
			ep.currentpageurl = np

def getnextpageurl(pagenumber, html, **kw):
	r = re.search("href=\"([^\"]+?-{})\"".format(pagenumber+1), html)
	if r is None:
		return ""
	else:
		return r.group(1)
		