"""
https://www.instagram.com/haneame_cos/?hl=zh-tw
"""

import re
import json
from urllib.parse import urlencode, parse_qs, urlparse
from html import unescape

from ..core import Episode
from ..error import is_http, SkipEpisodeError

domain = ["www.instagram.com"]
name = "Instagram"
noepfolder = True

cache_next_page = {}
config = {
	"cookie_sessionid": ""
}

def get_title(html, url):
	title = re.search("<title>([^<]+)", html).group(1)
	return "[instagram] {}".format(unescape(title).strip())
	
def get_episodes_from_data(data):
	user = data["user"]
	timeline = user["edge_owner_to_timeline_media"]
	eps = []
	for item in timeline["edges"]:
		eps.append(Episode(
			str(item["node"]["shortcode"]),
			"https://www.instagram.com/p/{}/".format(item["node"]["shortcode"])
		))
	end_cursor = None
	if timeline["page_info"]["has_next_page"]:
		end_cursor = timeline["page_info"]["end_cursor"]
	return reversed(eps), end_cursor
	
def build_next_page(key, cursor, user_id):
	cache_next_page[key] = "https://www.instagram.com/graphql/query/?{}".format(urlencode({
		"query_hash": "2c5d4d8b70cad329c4a6ebe3abb6eedd",
		"variables": json.dumps({
			"id": user_id,
			"first": 12,
			"after": cursor
		})
	}))

def get_episodes(html, url):
	if re.match(r"https://www\.instagram\.com/graphql/query/", url):
		body = json.loads(html)
		eps, cursor = get_episodes_from_data(body["data"])
		if cursor:
			variables = parse_qs(urlparse(url).query)["variables"][0]
			variables = json.loads(variables)
			build_next_page(url, cursor, variables["id"])
		return eps

	if re.match(r"https://www\.instagram\.com/[^/]+/", url):
		# get episodes from init data
		data = get_init_data(html, "ProfilePage")
		eps, cursor = get_episodes_from_data(data)
		if cursor:
			build_next_page(url, cursor, data["user"]["id"])
		return eps
		
	raise Exception("unknown URL: {}".format(url))
	
def get_init_data(html, page):
	shared_data = re.search("window\._sharedData = ([\s\S]+?);</script", html).group(1)
	shared_data = json.loads(shared_data)
	return shared_data["entry_data"][page][0]["graphql"]
	
def get_extra_data(html):
	text = re.search("window\.__additionalDataLoaded\('[^']+',(.*?)\);</script>", html).group(1)
	return json.loads(text)

def find_media(media):
	if "video_versions" in media:
		return max(media["video_versions"], key=lambda i: i["height"])["url"]
	return max(media["image_versions2"]["candidates"], key=lambda i: i["height"])["url"]
	
def get_images(html, url):
	result = []
	data = get_extra_data(html)
	for item in data["items"]:
		if item.get("carousel_media", None):
			result += [find_media(m) for m in item["carousel_media"]]
		else:
			result.append(find_media(item))
	return result

def get_next_page(html, url):
	return cache_next_page.get(url)

def errorhandler(err, crawler):
	if is_http(err, 404) and re.match(r"https://www\.instagram\.com/p/[^/]+/", err.response.url):
		raise SkipEpisodeError(True)
	
