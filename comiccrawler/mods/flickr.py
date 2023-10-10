#! python3

"""this is flickr module for comiccrawler

Ex:
	https://www.flickr.com/photos/133767722@N08/
	https://www.flickr.com/photos/dio-tw/

"""

import re
import json
from urllib.parse import urljoin
from html import unescape

from deno_vm import eval

from ..core import Episode, grabhtml
from ..error import is_http, SkipEpisodeError

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
			image = None
		else:
			sizes = get_sizes(photo)
			max_size = max(sizes, key=lambda s: s.get("width", 0))
			image = urljoin(url, max_size["url"])
			
		eps.append(Episode(title, ep_url, image=image))

	return eps[::-1]
	
def get_sizes(photo):
	# photo is a dict
	sizes = {}
	for key, value in photo.items():
		match = re.match("([a-z]+)_([a-z0-9]{1,2})$", key)
		if not match:
			continue
		prop, name = match.groups()
		if name not in sizes:
			sizes[name] = {"name": name}
		sizes[name][prop] = value
	return sizes.values()
	
def query_photos(url, key, nsid, page):
	params = {
		"per_page": 100,
		"page": page,
		"extras": "media,url_sq,url_q,url_t,url_s,url_n,url_w,url_m,url_z,url_c,url_l,url_h,url_k,url_3k,url_4k,url_f,url_5k,url_6k,url_o",
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
	# pylint: disable=no-member
	# https://github.com/PyCQA/pylint/issues/922
	rs = json.loads(rs)
	return (rs.get("photos") or rs.get("photoset"))["photo"]
	
def query_video(id, secret, key):
	rs = grabhtml("https://api.flickr.com/services/rest", params={
		"photo_id": id,
		"secret": secret,
		"method": "flickr.video.getStreamInfo",
		"api_key": key,
		"format": "json",
		"nojsoncallback": "1"
	})
	rs = json.loads(rs)
	return sorted(rs["streams"]["stream"], key=key_func)[-1]["_content"]
		
prior = {
	"orig": float("inf"),
	"appletv": 720,
	"iphone_wifi": 360
}

def key_func(stream):
	if stream["type"] in prior:
		return prior[stream["type"]]
	if isinstance(stream["type"], str):
		return int(re.match("[\d.]+", stream["type"]).group())
	return stream["type"]
	
def get_images(html, url):
	key = re.search('root\.YUI_config\.flickr\.api\.site_key = "([^"]+)', html).group(1)
	model = re.search(r"Y\.ClientApp\.init\(([\s\S]+?)\)\s*\.then", html).group(1)
	js = """
	const auth = null, reqId = null;
	const model = """ + model + """;
	model.modelExport.main["photo-models"][0]
	"""
	data = eval(js)
	if data.get("mediaType") == "video":
		return query_video(data["id"], data["secret"], key)
	max_size = max(data["sizes"].values(), key=lambda s: s.get("width", 0))
	return urljoin(url, max_size["url"])

def get_next_page(html, url):
	match = re.search('rel="next"\s+href="([^"]+)', html)
	if match:
		return urljoin(url, match.group(1))
		
def errorhandler(err, crawler):
	if is_http(err, 410) or is_http(err, 404):
		if (re.match(r"https://(live|farm\d+)\.staticflickr\.com/\d+/\d+_[a-z0-9]+_[a-z0-9]{1,2}\.\w+", err.response.url) and
				crawler.ep.image):
			# a specific size is deleted?
			crawler.ep.image = None
			# clear html to refetch the page
			crawler.html = None
			return
			
		if re.match(r"https://www\.flickr\.com/photos/[^/]+/\d+/", err.response.url):
			raise SkipEpisodeError
