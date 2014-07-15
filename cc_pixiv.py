#! python3

"""this is pixiv module for comiccrawler

Ex:
	http://www.pixiv.net/member_illust.php?id=2211832

"""

import re
from comiccrawler import Episode, ConfigManager, grabhtml, LastPageError
from safeprint import safeprint

header = {
	"User-Agent": "Mozilla/5.0 (Windows NT 6.1; WOW64; rv:23.0) Gecko/20100101 Firefox/23.0",
	"Referer": "http://www.pixiv.net/member_illust.php"
}
domain = ["www.pixiv.net"]
name = "Pixiv"
noepfolder = True

def loadconfig(config):
	if name not in config:
		config[name] = {}
	ConfigManager.apply(config[name], {
		"SESSID": "請輸入Cookie中的PHPSESSID"
	})
	header["Cookie"] = "PHPSESSID=" + config[name]["SESSID"]

def gettitle(html, **kw):
	if "pixiv.user.loggedIn = true" not in html:
		raise Exception("you didn't login!")
	user = re.search("class=\"user\">(.+?)</h1>", html).group(1)
	id = re.search("pixiv.context.userId = '(\d+)'", html).group(1)
	return "{} - {}".format(id, user)
	
def getepisodelist(html, url=""):
	s = []
	base = re.search("(https?://.+)\?", url).group(1)
	while True:
		ms = re.findall("<a href=\"([^\"]+)\" class=\"work ?\"><div class=\"_layout-thumbnail\"><img[^>]+></div><h1 class=\"title\" title=\"([^\"]+)\">", html)
		# safeprint(ms)
		for m in ms:
			url, title = m
			uid = re.search("id=(\d+)", url).group(1)
			e = Episode()
			e.title = "{} - {}".format(uid, title)
			e.firstpageurl = base + url
			s.append(e)
			
		un = re.search("href=\"([^\"]+)\" rel=\"next\"", html)
		if un is None:
			break
		u = un.group(1).replace("&amp;", "&")
		safeprint(base + u)
		html = grabhtml(base + u, hd=header)
	# safeprint(s)
	return s[::-1]

def getimgurls(html, url=""):
	if "pixiv.user.loggedIn = true" not in html:
		raise Exception("you didn't login!")
	try:
		img = re.search("\"works_display\"><[^>]+><img src=\"([^\"]+)\"", html).group(1)
		pages = re.search("(\d+)P</li>", html)
		if pages is None:
			return [img.replace("_m", "")]
		pages = int(pages.group(1))
		s = [img.replace("_m", "_big_p{}".format(i)) for i in range(pages)]
		return s
	except Exception as er:
		restrict = re.search('<section class="restricted-content">', html)
		if restrict:
			raise RestrictPageError
		raise er

class RestrictPageError(Exception):
	pass
		
def errorhandler(er, ep):
	if type(er) == RestrictPageError:
		ep.skip = True
		raise LastPageError
		
	# http://i1.pixiv.net/img21/img/raven1109/10841650_big_p0.jpg
	from urllib.error import HTTPError
	if type(er) == HTTPError and er.code == 404 and "imgurls" in dir(ep):
		p = ep.currentpagenumber - 1
		ep.imgurls[p] = ep.imgurls[p].replace("_big_", "_")
		return True
		
	# http://www.pixiv.net/member_illust.php?mode=medium&illust_id=43620872
	if (type(er) == HTTPError and er.code == 404 and 
			'span class="error"' in er.read().decode()):
		ep.skip = True
		return True

def getnextpageurl(pagenumber, html, url=""):
	pass
	