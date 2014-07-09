#! python3
"""
http://manhua.dmzj.com/fklmfsnyly/

"""

import re
import comiccrawler
import execjs

"""
Dictionary header. It contains cookie, user-agent, referer..., etc.
List domain. If the input url match the domain, the downloader will be
set to this module.
String name. Module name, will be show on the gui.
"""
header = {}
domain = ["manhua.dmzj.com"]
name = "動漫之家"

def gettitle(html, url):
	"""gettitle(html, url="") -> title string
	
	The user input url should match your domain. html is the source of url.
	Title will be used in image saving filepath, so becareful of duplicate 
	title.
	"""
	return re.search("<h1>(.+?)</h1>", html).group(1)
	
def getepisodelist(html, url):
	"""getepisodelist(html, url) -> Mission list
	
	The mission list should be sorted by date, latest at last, so the 
	downloader will download oldest first.
	"""
	
	base = re.search("(https?://[^/]+)", url).group(1)
	comicurl = re.search("comic_url = \"(.+?)\"", html).group(1)
	ms = re.findall("href=\"(/{}.+?)\" (?: class=\"color_red\")?>(.+?)</a></li>".format(comicurl), html)
	s = []
	for m in ms:	
		url, title = m
		e = comiccrawler.Episode()
		e.title = title
		# safeprint(e.title)
		e.firstpageurl = base + url
		# print(e.firstpageurl)
		s.append(e)
	return s

"""
There are two methods to get images url. If you can get all urls from the 
first page, then use getimgurls. If you have to download each pages to get
image url, use getimgurl and nextpage functions.

Note that you should only implement one of two methods. Never write 
getimgurls and getimgurl both.
"""

def getimgurls(html, url):
	"""getimgurls(html, url) -> url list
	
	Return a list of urls.
	"""
	
	html = html.replace("\n", "")
	s = re.search("page = '';(.+?);var g_comic_name", html).group(1)
	ctx = execjs.compile(s)
	pages = execjs.eval(ctx.eval("pages"))
	base = "http://imgfast.dmzj.com/"
	
	return [base + page for page in pages]
	
def errorhandler(er, ep):
	"""errorhandler(error, episode) -> void
	
	Downloader will call errorhandler if there is an error happened when
	downloading image. Normally it does nothing.
	"""
	
	pass
	