#! python3

import re
from html import unescape

from ..core import Episode, grabhtml
from ..safeprint import safeprint

domain = ["tsundora.com"]
name = "tsundora"
noepfolder = True

def gettitle(html, url):
	title = re.search(r'top_title">([^<]+)', html).group(1)
	return "[tsundora] " + title

def getepisodelist(html, url):
	s = []
	# base = re.search("(https?://[^/]+)", url).group(1)
	while True:
		match = None
		for match in re.finditer(r'href="(http://tsundora\.com/(\d+))"class="img_hover_trans" title="([^"]+)"', html):
			url, id, title = match.groups()
			s.append(Episode(id + " - " + title, url))

		if not match:
			break

		next_url = re.search(r"rel='next' href='([^']+)'", html).group(1)
		safeprint(next_url)
		html = grabhtml(next_url)
	return s[::-1]

def getimgurls(html, url):
	img = re.search(r'post-img">\s*<a href="([^"]+)"', html).group(1)
	return [img]
