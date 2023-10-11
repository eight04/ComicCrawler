#! python3

"""this is deviant module for comiccrawler, support deviantart.com

2014/7/13
JDownloader2 now support　deviantart.com!

"""

import re
import json
from html import unescape
from urllib.parse import urlparse

from deno_vm import eval

from ..error import PauseDownloadError
from ..core import Episode
from ..url import update_qs

domain = ["deviantart.com"]
name = "dA"
noepfolder = True
config = {
	"cookie_auth": "",
	"cookie_auth_secure": "",
	"cookie_userinfo": ""
}

def get_title(html, url):
	id = urlparse(url).path[1:]
	return f"[dA] {id}"
	
def check_login(state):
	if not state["@@publicSession"]["isLoggedIn"]:
		raise PauseDownloadError("You didn't login")		
		
next_page_cache = {}
		
def get_episodes_from_api(source, url):
	data = json.loads(source)
	s = []
	for item in data["results"]:
		d = item["deviation"]
		s.append(Episode(
			f"{d['deviationId']} - {d['title']}",
			d["url"]
		))
		
	if data["hasMore"]:
		next_page_cache[url] = update_qs(url, {
			"offset": data["nextOffset"]
		})
		
	return s[::-1]
	
def get_state(html):
	js = re.search(r"(window\.__INITIAL_STATE__[\s\S]+?)</script>", html).group(1)
	return eval("""
		const window = {};
	""" + js + """
		; window.__INITIAL_STATE__
	""")	

def get_episodes(html, url):
	if "_napi" in url:
		return get_episodes_from_api(html, url)
		
	state = get_state(html)
	check_login(state)

	deviation = state["@@entities"]["deviation"]
	gallery = None
	for key, value in state["@@streams"].items():
		if key.startswith("folder-deviations-gallery"):
			gallery = value
			break
	s = []
	for id in gallery["items"]:
		d = deviation[str(id)]
		s.append(Episode(
			f"{id} - {d['title']}",
			d["url"]
		))
		
	if gallery["hasMore"]:
		username = next(iter(state["@@entities"]["user"].values()))["username"]
		params = {
			"username": username,
			"offset": gallery["nextOffset"],
			"limit": gallery["itemsPerFetch"],
			# FIXME: it seems that this param is not used with featured galleries?
			"mode": "newest"
		}
		folder_id = gallery["streamParams"]["folderId"]
		if folder_id < 0:
			params["all_folder"] = "true"
		else:
			params["folderid"] = folder_id
		next_page_cache[url] = update_qs(
			"https://www.deviantart.com/_napi/da-user-profile/api/gallery/contents",
			params)
		
	return s[::-1]

def get_images(html, url):
	state = get_state(html)
	check_login(state)

	try:
		i = re.search('href="(https://www.deviantart.com/download[^"]+)', html).group(1)
		return [unescape(i)]
	except AttributeError:
		pass
		
	id = re.search(r"\d+$", url).group()
	media = state["@@entities"]["deviation"][id]["media"]
	return [f"{media['baseUri']}?token={media['token'][-1]}"]
	
def get_next_page(html, url):
	if url in next_page_cache:
		return next_page_cache.pop(url)
