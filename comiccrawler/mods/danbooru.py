#! python3

"""this is danbooru module for comiccrawler

Ex:
	https://danbooru.donmai.us/posts?tags=fault!!

"""

import re
from html import unescape
from urllib.parse import urljoin

from ..core import Episode, grabhtml

domain = ["danbooru.donmai.us"]
name = "Danbooru"
noepfolder = True

def get_title(html, url):
	title = re.search(r"<title>(.+?)</title>", html, re.DOTALL).group(1)
	return title.strip()

def get_episodes(html, url):
	s = []
	for match in re.finditer(r'href="(/posts/(\d+)[^"]*)"', html):
		u = match.group(1)
		title = match.group(2)
		e = Episode(title, urljoin(url, u))
		s.append(e)

	return s[::-1]

def get_images(html, url):
	pos = re.search(r"image-container", html).start()
	img = re.compile(r'data-file-url="([^"]+)"').search(html, pos).group(1)
	return [urljoin(url, img)]

def get_next_page(html, url):
	m = (re.search(r'"([^"]+)" rel="next"', html) or
		re.search(r'<a rel="next" href="([^"]+)', html))
	if m:		
		return urljoin(url, unescape(u.group(1)))
