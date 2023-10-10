#! python3
"""The module for m.dmzj.com

Ex. http://m.dmzj.com/info/qiyuanzui.html
"""

import re
from urllib.parse import urljoin

from deno_vm import eval

from ..core import Episode

domain = ["m.dmzj.com"]
name = "動漫之家M"

def get_title(html, url):
	return re.search('comicName">([^<]+)', html).group(1)

def get_episodes(html, url):
	data_js = re.search("initIntroData(.+?);", html, re.DOTALL).group(1)
	data = eval(data_js)

	ep_data = []
	for category in data:
		ep_data += category["data"]
	ep_data = sorted(ep_data, key=lambda data: data["chapter_order"])

	episodes = []

	for data in ep_data:
		ep_url = "/view/{}/{}.html".format(data["comic_id"], data["id"])
		title = data["title"] + data["chapter_name"]
		episodes.append(Episode(title, urljoin(url, ep_url)))

	return episodes

def get_images(html, url):
	pages_js = re.search(r'page_url":(\[[^\]]+\])', html).group(1)
	pages = eval(pages_js)

	# thumbs.db?!
	# http://manhua.dmzj.com/zhuoyandexiana/3488-20.shtml
	return [page for page in pages if page and not page.lower().endswith("thumbs.db")]
