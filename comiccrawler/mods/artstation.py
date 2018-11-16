#! python3

"""
https://www.artstation.com/taekwonkim
"""


import json
import math
import re

from node_vm2 import eval

from ..url import urljoin, urlparse, parse_qs, update_qs
from ..core import Episode
from ..error import SkipPageError

domain = ["www.artstation.com"]
name = "ArtStation"
noepfolder = True

EP_PER_PAGE = 50

def get_title(html, url):
	return re.search(r'<title>([^<]*)', html).group(1)
	
def is_project(url):
	return re.search("/users/[^/]+/projects\.json", url)
	
def is_user_home(url):
	return re.search("www\.artstation\.com/[^/]+$", url)

def get_episodes(html, url):
	if is_project(url):
		return [Episode(
			title="{id} - {title} ({hash_id})".format_map(d),
			url=d["permalink"],
		) for d in reversed(json.loads(html)["data"])]
	raise SkipPageError

def get_images(html, url):
	hash = re.search("/artwork/([^/]+)", url).group(1)
	pattern = "cache\.put\('/projects/{hash}\.json', ('.+?')\);$".format(hash=hash)
	data_json = eval(re.search(pattern, html, re.M).group(1))
	data = json.loads(data_json)
	return [a["image_url"] for a in data["assets"]]
	
def get_next_page(html, url):
	if is_project(url):
		page = int(parse_qs(urlparse(url).query)["page"][0])
		total_page = math.ceil(json.loads(html)["total_count"] / EP_PER_PAGE)
		return update_qs(url, {"page": page + 1}) if page < total_page else None
			
	if is_user_home(url):
		user = re.search("www\.artstation\.com/([^/]+)", url).group(1)
		return urljoin(url, "/users/{user}/projects.json?page=1".format(user=user))
