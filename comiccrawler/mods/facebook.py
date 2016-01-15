#! python3

"""this is facebook module for comiccrawler

Ex:
	https://www.facebook.com/gtn.moe/photos/pcb.942148229165656/942147902499022/?type=3&theater

"""

import re
from urllib.parse import urljoin
from html import unescape
from ..core import Episode

domain = ["www.facebook.com"]
name = "FB"
circular = True
noepfolder = True

def gettitle(html, url):
	id = re.search(r"photos/([^/]+)", url).group(1)
	title = re.search("<title[^>]*>([^<]+)", html).group(1)
	return unescape("{} ({})".format(title, id))

def getepisodelist(html, url):
	return [Episode("image", url)]

def getimgurl(html, url, page):
	id = re.search(r"photos/[^/]+/(\d+)", url).group(1)
	return urljoin(url, "/photo/download/?fbid=" + id)

def getnextpageurl(html, url, page):
	next_url = re.search('photoPageNextNav"[^>]*?href="([^"]+)', html).group(1)
	return urljoin(url, next_url)
