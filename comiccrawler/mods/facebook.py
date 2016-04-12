#! python3

"""this is facebook module for comiccrawler

Ex:
	https://www.facebook.com/gtn.moe/photos/pcb.942148229165656/942147902499022/?type=3&theater
	https://www.facebook.com/Nisinsheep/photos/pcb.1667254973516031/1667254333516095/?type=3&theater
	https://www.facebook.com/photo.php?fbid=10202533447211476&set=a.10202533447131474.1073741835.1654599523&type=3&theater

"""

import re, urllib.parse, json
# from urllib.parse import urljoin
from html import unescape
from ..core import Episode, grabhtml

domain = ["www.facebook.com"]
name = "FB"
circular = True
noepfolder = True

def get_title(html, url):
	try:
		id = re.search(r"photos/([^/]+)", url).group(1)
	except AttributeError:
		id = re.search("set=([^&]+)", url).group(1)
	title = re.search("<title[^>]*>([^<]+)", html).group(1)
	return unescape("{} ({})".format(title, id))

def get_episodes(html, url):
	return [Episode("image", url)]

def get_images(html, url):
	try:
		id = re.search(r"photos/[^/]+/(\d+)", url).group(1)
	except AttributeError:
		id = re.search("fbid=([^&]+)", url).group(1)
	return urllib.parse.urljoin(url, "/photo/download/?fbid=" + id)

def get_next_page(html, url):
	match = re.search('photoPageNextNav"[^>]*?href="([^"]+)', html)
	if match:
		return urllib.parse.urljoin(url, match.group(1))
		
	fbset, fbid = re.search('photos/([^/]+)/([^/]+)', url).groups()
	query = urllib.parse.urlencode({
		"data": json.dumps({"fbid": fbid, "set": fbset}),
		"__a": 1
	})
	pagelet = grabhtml("https://www.facebook.com/ajax/pagelet/generic.php/PhotoViewerInitPagelet?" + query)
	
	next_id = re.search(r'"addPhotoFbids".*?(\d+)', pagelet).group(1)
	return urllib.parse.urljoin(url, "../" + next_id + "/")
	