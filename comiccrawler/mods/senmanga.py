#! python3

"""module for senmanga
http://raw.senmanga.com/Overlord/
"""

import re

from ..core import Episode
from ..url import urljoin

domain = ["raw.senmanga.com"]
name = "senmanga"

def get_title(html, url):
	return re.search(r'<h1 class="title"><a[^>]*>([^<]+)', html).group(1)

def get_episodes(html, url):
	prefix = re.escape(url)
	s = []
	for m in re.finditer(r'<a href="({}/[^/"]+/[^"]+)"[^>]*>([^<]+)'.format(prefix), html):
		ep_url, title = m.groups()
		s.append(Episode(title, urljoin(url, ep_url)))
	return s[::-1]

def get_images(html, url):
	return re.search(r'<img src="([^"]+?/viewer/[^"]+)', html).group(1)
	
def get_next_page(html, url):
	match = re.search('<a href="([^"]+)"><[^>]+>Next Page</span>', html)
	if match:
		next_page_url = urljoin(url, match.group(1))
		if get_ep_from_url(url) == get_ep_from_url(next_page_url):
			return next_page_url

def get_ep_from_url(url):
	match = re.match("https://raw\.senmanga\.com/([^/]+)/([^/]+)(?:/([^/]+))?", url)
	_name, ep, _page = match.groups()
	return ep
