#! python3
"""
This is an example of how to implement comiccrawler module.

"""

import re
import comiccrawler

"""
Dictionary header. It contains cookie, user-agent, referer..., etc.
List domain. If the input url match the domain, the downloader will be
set to this module.
String name. Module name, will be show on the gui.
"""
header = {
	"Referer": "http://www.example.com"
}
domain = ["www.example.com", "comic.example.com"]
name = "This Is an Example"


def loadconfig(config):
	"""loadfunction(config) -> void

	This function will be called when module load first time. config is an 
	object of configparser.ConfigParser.
	"""
	if name not in config:
		# defult value
		config[name] = {
			"user": "user-default-value",
			"hash": "hash-default-value"
		}
	header["Cookie"] = "user={}; hash={}".format(
			config[name]["user"], config[name]["hash"])

def gettitle(html, url):
	"""gettitle(html, url="") -> title string
	
	The user input url should match your domain. html is the source of url.
	Title will be used in image saving filepath, so becareful of duplicate 
	title.
	"""
	return re.search("<h1 id='title'>(.+?)</h1>", html).group(1)
	
def getepisodelist(html, url):
	"""getepisodelist(html, url) -> Mission list
	
	The mission list should be sorted by date, latest at last, so the 
	downloader will download oldest first.
	"""
	
	base = re.search("(https?://[^/]+)", url).group(1)
	ms = re.findall("<a href='(.+?)'>(.+?)</a>", html)
	s = []
	for m in ms:	
		u, title = m
		e = comiccrawler.Episode()
		e.title = title
		e.firstpageurl = base + url
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
	
	ms = re.findall("<img src='(.+?)'>", html)
	return [m[0] for m in ms]
	
def getimgurl(html, page, url):
	"""getimgurl(html, page, url) -> url string"""
	
	return re.search("<img id='showimage' src='(.+?)'>", html).group(1)
	
def getnextpageurl(page, html, url):
	"""getnextpageurl(page, html, url) -> url string or empty string
	
	If this page is the last page, you should return empty string, else 
	you should return the url of next page. Yeah I know I just misaround 
	with getimgurl's params.
	"""
	
	r = re.search("<a id='nextpage' href='(.+?)'>next</a>", html)
	if r is None:
		return ""
	return r.group(1)
		
def errorhandler(er, ep):
	"""errorhandler(error, episode) -> void
	
	Downloader will call errorhandler if there is an error happened when
	downloading image. Normally it does nothing.
	"""
	
	pass
	