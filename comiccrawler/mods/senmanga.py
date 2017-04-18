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
	return re.search(r'<h1 itemprop="name"><a[^>]*>([^<]+)', html).group(1)

def get_episodes(html, url):
	start = html.index("<h1>Chapters List</h1>")
	end = html.index('<aside id="sidebar">')
	html = html[start:end]
	s = []
	
	for m in re.finditer(r'<a href="([^"]+)"[^>]*>([^<]+)', html):
		ep_url, title = m.groups()
		s.append(Episode(title, urljoin(url, ep_url)))
	return s[::-1]

def get_images(html, url):
	return url.replace("raw.senmanga.com", "raw.senmanga.com/viewer")
	
def get_next_page(html, url):
	match = re.search('<a href="([^"]+)"><span >Next Page</span>', html)
	if match:
		return urljoin(url, match.group(1))
