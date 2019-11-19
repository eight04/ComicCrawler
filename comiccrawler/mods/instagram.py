"""
https://www.instagram.com/haneame_cos/?hl=zh-tw
"""

import re
import json
from urllib.parse import urlencode
from html import unescape

from ..core import Episode

domain = ["www.instagram.com"]
name = "Instagram"
noepfolder = True

cache_next_page = {}

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
	next_page = None
	if timeline["page_info"]["has_next_page"]:
		next_page = "https://www.instagram.com/graphql/query/?{}".format(urlencode({
			"query_hash": "2c5d4d8b70cad329c4a6ebe3abb6eedd",
			"variables": json.dumps({
				"id": user["id"],
				"first": 12,
				"after": timeline["page_info"]["end_cursor"]
			})
		}))
	return eps, next_page

def get_episodes(html, url):
	if re.match(r"https://www\.instagram\.com/graphql/query/", url):
		body = json.loads(html)
		eps, next_page = get_episodes_from_data(body["data"])
		if next_page:
			cache_next_page[url] = next_page
		return eps

	if re.match(r"https://www\.instagram\.com/[^/]+/", url):
		# get episodes from init data
		eps, next_page = get_episodes_from_data(get_init_data(html))
		if next_page:
			cache_next_page[url] = next_page
		return eps
		
	raise Exception("unknown URL: {}".format(url))
	
def get_init_data(html):
	shared_data = re.search("window\._sharedData = ([\s\S]+?);</script", html).group(1)
	shared_data = json.loads(shared_data)
	return shared_data["entry_data"]["ProfilePage"][0]["graphql"]
	
def get_images(html, url):
	media = get_init_data(html)["shortcode_media"]
	try:
		video = media["video_url"]
	except KeyError:
		pass
	else:
		if video:
			return video
		
	try:
		sidecard_children = media["edge_sidecar_to_children"]["edges"]
	except KeyError:
		pass
	else:
		if sidecard_children:
			return [e["node"]["display_url"] for e in sidecard_children]
			
	return media["display_url"]

def get_next_page(html, url):
	return cache_next_page.get(url)
