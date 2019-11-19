#! python3

import json
import re
from urllib.parse import urlparse, parse_qs

from ..episode import Episode
from ..error import SkipPageError
from ..url import update_qs
from ..grabber import grabhtml

domain = ["beta.sankakucomplex.com"]
name = "Sankaku Beta"
noepfolder = True

data_len_cache = {}

class ExpireError(Exception):
	pass

def get_query(url, name):
	query = urlparse(url).query
	return parse_qs(query)[name][0]

def get_title(html, url):
	return "[sankaku] {}".format(get_query(url, "tags"))

def get_episodes(html, url):
	if re.match(r"https://beta\.sankakucomplex\.com/\?", url):
		raise SkipPageError
		
	data = json.loads(html)
	data_len_cache[url] = len(data)
	return [
		Episode(
			str(e["id"]),
			"https://beta.sankakucomplex.com/post/show/{}".format(e["id"]),
			image=e["file_url"]
		) for e in reversed(data)
	]

def get_images(html, url):
	id = re.search("post/show/(\d+)", url).group(1)
	data = grabhtml("https://capi-v2.sankakucomplex.com/posts?lang=english&page=1&limit=1&tags=id_range:{}".format(id))
	data = json.loads(data)
	return data[0]["file_url"]

def get_next_page(html, url):
	if re.match(r"https://beta\.sankakucomplex\.com/\?", url):
		return update_qs("https://capi-v2.sankakucomplex.com/posts?lang=english&page=1&limit=40", {
			"tags": "hide_posts_in_books:never {}".format(get_query(url, "tags"))
		})
		
	if "https://capi-v2.sankakucomplex.com/posts" in url:
		if data_len_cache[url] >= 40:
			return update_qs(url, {
				"page": int(get_query(url, "page")) + 1
			})
			
def redirecthandler(response, crawler):
	if re.match(r"https://chan\.sankakucomplex\.com/.+\.(png|jpg)", response.url):
		raise ExpireError

def errorhandler(err, crawler):
	if isinstance(err, ExpireError):
		crawler.ep.image = None
		crawler.html = None
		