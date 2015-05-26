#! python3
"""
This is an example to showcase how to build a comiccrawler module.

"""

import re
import comiccrawler

# The header used in grabber method
header = {
	"Referer": "http://www.example.com"
}

# Match domain
domain = ["www.example.com", "comic.example.com"]

# Module name
name = "This Is an Example"

# With noepfolder = True, Comic Crawler won't generate subfolder for each episode.
noepfolder = False

# Wait 5 seconds between each page
rest = 5

# Specific user settings
config = {
	"user": "user-default-value",
	"hash": "hash-default-value"
}

def loadconfig():
	"""This function will be called each time the config reloaded.
	"""
	header["Cookie"] = "user={}; hash={}".format(config["user"], config["hash"])

def gettitle(html, url):
	"""Return mission title.
	
	Title will be used in saving filepath, so be sure to avoid duplicate title.
	"""
	return re.search("<h1 id='title'>(.+?)</h1>", html).group(1)
	
def getepisodelist(html, url):
	"""Return episode list.
	
	The episode list should be sorted by date, latest at last, so the 
	downloader will download the oldest first.
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
	"""Return the list of all images"""
	
	ms = re.findall("<img src='(.+?)'>", html)
	return [m[0] for m in ms]
	
def getimgurl(html, page, url):
	"""Return the url of the image"""
	
	return re.search("<img id='showimage' src='(.+?)'>", html).group(1)
	
def getnextpageurl(page, html, url):
	"""Return the url of the next page. Return '' if this is the last page.
	"""
	
	r = re.search("<a id='nextpage' href='(.+?)'>next</a>", html)
	if r is None:
		return ""
	return r.group(1)
		
def errorhandler(er, ep):
	"""Downloader will call errorhandler if there is an error happened when
	downloading image. Normally you can just skip this function.
	"""
	pass
	