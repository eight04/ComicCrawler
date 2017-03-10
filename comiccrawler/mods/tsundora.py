#! python3

import re

from ..core import Episode

domain = ["tsundora.com"]
name = "tsundora"
noepfolder = True

def get_title(html, url):
	title = re.search(r'top_title">([^<]+)', html).group(1)
	return "[tsundora] " + title

def get_episodes(html, url):
	s = []
	# base = re.search("(https?://[^/]+)", url).group(1)
	match = None
	for match in re.finditer(
			r'href="(http://tsundora\.com/(\d+))"class="img_hover_trans"'
			'title="([^"]+)"', html):
		url, id, title = match.groups()
		s.append(Episode(id + " - " + title, url))
	return s[::-1]

def get_images(html, url):
	img = re.search(r'post-img">\s*<a href="([^"]+)"', html).group(1)
	return [img]

def get_next_page(html, url):
	match = re.search(r"rel='next' href='([^']+)'", html)
	if match:
		return match.group(1)
	