#! python3

"""this is flickr module for comiccrawler

Ex:
	https://www.flickr.com/photos/133767722@N08/
	https://www.flickr.com/photos/dio-tw/

"""

import re
import json
import math

from urllib.parse import urljoin
from html import unescape

from ..core import Episode, grabhtml

domain = ["www.flickr.com"]
name = "flickr"
noepfolder = True

def get_title(html, url):
	title = unescape(re.search("<title>([^<]+)</title>", html).group(1)[:-9])
	user = url.partition("/photos/")[2].strip("/")
	return "[flickr] {title} ({user})".format(title=title, user=user)

def get_episodes(html, url):
	eps = []
	
	key = re.search('root.YUI_config.flickr.api.site_key = "([^"]+)', html).group(1)
	nsid = re.search('"nsid":"([^"]+)', html).group(1)
	base = re.match('.+?/photos/[^/]+', url).group()
	match = re.search(r"/page(\d+)", url)
	if match:
		page = int(match.group(1))
	else:
		page = 1
	
	for photo in query_photos(url, key, nsid, page):
		title = "{id} - {title}".format_map(photo)
		ep_url = "{base}/{id}/".format(base=base, id=photo["id"])
		
		if photo.get("media") == "video":
			image = query_video(photo, key)
		else:
			image = urljoin(url, find_largest(photo))
			
		eps.append(Episode(title, ep_url, image=image))

	return eps[::-1]
	
def query_photos(url, key, nsid, page):
	params = {
		"per_page": 100,
		"page": page,
		"extras": "media,url_c,url_f,url_h,url_k,url_l,url_m,url_n,url_o,url_q,url_s,url_sq,url_t,url_z",
		"api_key": key,
		"format": "json",
		"nojsoncallback": 1
	}
	match = re.search("/(?:sets|albums)/([^/]+)", url)
	if match:
		set_id = match.group(1)
		params["method"] = "flickr.photosets.getPhotos"
		params["photoset_id"] = set_id
	else:
		params["method"] = "flickr.people.getPhotos"
		params["user_id"] = nsid
		
	rs = grabhtml("https://api.flickr.com/services/rest", params=params)
	rs = json.loads(rs)
	return (rs.get("photos") or rs.get("photoset"))["photo"]
	
def find_largest(photo):
	max_width = 0
	url = None
	
	for key, value in photo.items():
		match = re.match("url_(.+?)$", key)
		if not match:
			continue
		type = match.group(1)
		width = int(photo.get("width_" + type, 0))
		if width > max_width:
			max_width = width
			url = value
			
	return url
	
def query_video(data, key):
	rs = grabhtml("https://api.flickr.com/services/rest", params={
		"photo_id": data["id"],
		"secret": data["secret"],
		"method": "flickr.video.getStreamInfo",
		"api_key": key,
		"format": "json",
		"nojsoncallback": "1"
	})
	rs = json.loads(rs)
	return sorted(rs["streams"]["stream"], key=key_func)[-1]["_content"]
		
prior = {
	"orig": math.inf,
	"appletv": 720,
	"iphone_wifi": 360
}

def key_func(stream):
	if stream["type"] in prior:
		return prior[stream["type"]]
	if isinstance(stream["type"], str):
		return int(re.match("[\d.]+", stream["type"]).group())
	return stream["type"]

def get_next_page(html, url):
	match = re.search('rel="next"\s+href="([^"]+)', html)
	if match:
		return urljoin(url, match.group(1))
