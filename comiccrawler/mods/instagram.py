"""
https://www.instagram.com/haneame_cos/?hl=zh-tw
"""

import re
import json
from html import unescape
from urllib.parse import urlparse

from ..core import Episode
from ..error import is_http, SkipEpisodeError, SkipPageError
from ..url import update_qs
from ..session_manager import session_manager
from ..util import get_cookie

domain = ["www.instagram.com"]
name = "Instagram"
noepfolder = True

cache_next_page = {}
config = {
	"curl": r"""curl 'https://www.instagram.com/p/foo/' --compressed -H 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0' -H 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8' -H 'Accept-Language: zh-TW,en-US;q=0.7,en;q=0.3' -H 'Accept-Encoding: gzip, deflate, br' -H 'Connection: keep-alive' -H 'Upgrade-Insecure-Requests: 1' -H 'Sec-Fetch-Dest: document' -H 'Sec-Fetch-Mode: navigate' -H 'Sec-Fetch-Site: none' -H 'Sec-Fetch-User: ?1' -H 'Priority: u=4' -H 'Pragma: no-cache' -H 'Cache-Control: no-cache'""",
	"curl_api": ""
}
autocurl = True

def session_key(url):
	r = urlparse(url)
	if "api/v1" in r.path:
		return (r.scheme, r.netloc, "api")

def init_api_session(html):
	session = session_manager.get("https://www.instagram.com/api/v1/feed")
	if "X-CSRFToken" in session.headers:
		return
	token = get_cookie(session.cookies, "csrftoken", domain="www.instagram.com")
	app_id = re.search(r'"APP_ID":"([^"]+)', html).group(1)
	session.headers.update({
		"X-CSRFToken": token,
		"X-IG-App-ID": app_id,
		})

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
	
def get_episodes(html, url):
	if match := re.match(r"https://www\.instagram\.com/([^/]+)/", url):
		username = match.group(1)
		if username != "api":
			init_api_session(html)
			next_url = f"https://www.instagram.com/api/v1/feed/user/{username}/username/?count=12"
			cache_next_page[url] = next_url
			raise SkipPageError

	if "api/v1/feed" in url:
		body = json.loads(html)
		result = []
		for item in body["items"]:
			result.append(Episode(
				str(item["code"]),
				f"https://www.instagram.com/p/{item['code']}/"
			))
		
		if result and (next_max_id := body.get("next_max_id", None)):
			next_url = update_qs(url, {"max_id": next_max_id})
			cache_next_page[url] = next_url

		return result[::-1]
		
	raise ValueError("unknown URL: {}".format(url))
	
def get_init_data(html, page):
	shared_data = re.search(r"window\._sharedData = ([\s\S]+?);</script", html).group(1)
	shared_data = json.loads(shared_data)
	return shared_data["entry_data"][page][0]["graphql"]
	
def get_extra_data(html):
	text = re.search(r"window\.__additionalDataLoaded\('[^']+',(.*?)\);</script>", html).group(1)
	return json.loads(text)

def find_media(media):
	if media.get("video_versions", None):
		return max(media["video_versions"], key=lambda i: i["height"])["url"]
	return max(media["image_versions2"]["candidates"], key=lambda i: i["height"])["url"]

def extract_json(html, filter=None):
	for match in re.finditer(r'<script type="application/json"[^>]+>(.*?)</script>', html):
		text = match.group(1)
		if filter and not filter(text):
			continue
		yield json.loads(text)

def extract_json_value(data, key):
	# find object value in nested dict
	if isinstance(data, dict):
		for k, v in data.items():
			if k == key:
				yield v
			else:
				yield from extract_json_value(v, key)
	# find value in list
	elif isinstance(data, list):
		for item in data:
			yield from extract_json_value(item, key)
	
def get_images(html, url):
	# pid = re.search(r"https://www\.instagram\.com/p/([^/]+)/", url).group(1)
	result = []
	key = "xdt_api__v1__media__shortcode__web_info"
	for data in extract_json(html, filter=lambda s: key in s):
		for web_info in extract_json_value(data, key):
			for item in web_info["items"]:
				if item.get("carousel_media", None):
					result += [find_media(m) for m in item["carousel_media"]]
				else:
					result.append(find_media(item))
	# FIXME: there is no way to distinguash between request error and 404
	if "PolarisErrorRoot" in html:
		raise SkipEpisodeError(always=False)
	return result

def get_next_page(html, url):
	return cache_next_page.get(url)

def errorhandler(err, crawler):
	if is_http(err, 404) and re.match(r"https://www\.instagram\.com/p/[^/]+/", err.response.url):
		raise SkipEpisodeError(True)
	
