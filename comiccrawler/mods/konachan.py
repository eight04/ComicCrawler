#! python3

"""this is konachan module for comiccrawler

Ex:
	http://konachan.com/pool/show/218

"""

import re
from html import unescape
from urllib.parse import urljoin

from ..core import Episode
from ..error import SkipEpisodeError

domain = ["konachan.com"]
name = "Konachan"
noepfolder = True

def get_title(html, url):
	title = re.search(r"<title>/?(.+?) \|", html).group(1)
	return "[konachan] " + title
	
def get_episodes(html, url):
	s = []
	base = re.search("(https?://[^/]+)", url).group(1)
	for m in re.finditer('<a class="thumb" href="([^"]+)"', html):
		url = m.group(1)
		uid = re.search(r"show/(\d+)", url).group(1)
		e = Episode(uid, base + url)
		s.append(e)
	return s[::-1]

def get_images(html, url):
	try:
		img = re.search('href="([^"]+)" id="highres"', html).group(1)
	except AttributeError:
		if "This post was deleted" in html:
			raise SkipEpisodeError from None
		raise
	return urljoin(url, img)

def get_next_page(html, url):
	match = re.search('<a class="next_page" rel="next" href="([^"]+)">', html)
	if match:
		return urljoin(url, unescape(match.group(1)))
		