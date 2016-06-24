#! python3

"""this is acgn module for comiccrawler

Ex:
	http://comic.acgn.cc/manhua-murcielago.htm

"""

import re

from html import unescape

from ..core import Episode
from ..error import SkipEpisodeError

domain = ["comic.acgn.cc"]
name = "ACGN.cc"

def get_title(html, url):
	title = re.search(r"h3><a[^>]+>([^<]+)", html).group(1)
	return unescape(title)

def get_episodes(html, url):
	s = []
	cwd = re.search("https?://[^?]+/", url).group()

	for match in re.finditer(r'a href="(view-[^"]+)"[^>]*>([^<]+)<', html):
		u, title = match.groups()
		s.append(Episode(unescape(title), cwd + u))

	return s

def get_images(html, url):
	return [match.group(1) for match in re.finditer(r'_src="([^"]+)"', html)]

def errorhandler(err, crawler):
	if "暫缺" in crawler.ep.title:
		raise SkipEpisodeError
