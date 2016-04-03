#! python3

"""this is acgn module for comiccrawler

Ex:
	http://comic.acgn.cc/manhua-murcielago.htm

"""

import re, execjs
from html import unescape

from ..core import Episode
from ..error import SkipEpisodeError

domain = ["comic.acgn.cc"]
name = "ACGN.cc"

def gettitle(html, url):
	title = re.search(r"h3><a[^>]+>([^<]+)", html).group(1)
	return unescape(title)

def getepisodelist(html, url, last_episode):
	s = []
	cwd = re.search("https?://[^?]+/", url).group()

	for match in re.finditer(r'a href="(view-[^"]+)"[^>]*>([^<]+)<', html):
		u = match.group(1)
		title = match.group(2)
		e = Episode(unescape(title), cwd + u)
		s.append(e)

	return s[::-1]

def getimgurls(html, url):
	s = []
	for match in re.finditer(r'_src="([^"]+)"', html):
		u = match.group(1)
		s.append(u)
	return s

def errorhandler(err, ep):
	if "暫缺" in ep.title:
		raise SkipEpisodeError
