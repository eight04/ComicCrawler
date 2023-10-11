#! python3

"""
https://www.manhuaren.com/manhua-mofashaonvshenmedeyijinggoulela/
"""

import json
import re
from html import unescape
from urllib.parse import urljoin

from deno_vm import eval

from ..core import Episode

domain = ["www.manhuaren.com"]
name = "漫畫人"

def get_title(html, url):
	name = re.search('DM5_COMIC_MNAME=("[^"]+")', html).group(1)
	return json.loads(name)

def get_episodes(html, url):
	s = []
	pattern = 'href="(/m\d+/)[^>]+chapteritem[^>]+>([^<]+)'
	for match in re.finditer(pattern, html):
		ep_url, title = match.groups()
		s.append(Episode(unescape(title), urljoin(url, ep_url)))
	return s[::-1]
	
def get_images(html, url):
	js = re.search(r"(eval\([\s\S]+?)</script", html).group(1)
	return eval(js + ";newImgs")
