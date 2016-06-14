#! python3

import re

from urllib.parse import urljoin

from ..core import Episode

domain = ["imgbox.com"]
name = "imgbox"
noepfolder = True

def get_title(html, url):
	title = re.search(r'<h1>([^<]+)</h1>', html).group(1)
	title = re.sub(r" - \d+ images$", "", title)
	return "[imgbox] " + title

def get_episodes(html, url):
	s = []
	for match in re.finditer(r'href="(/(\w+))"><img', html):
		ep_url, id = match.groups()
		s.append(Episode(id, urljoin(url, ep_url)))
	return s

def get_images(html, url):
	img = re.search(r'href="([^?"]+\?download=true)"', html).group(1)
	return [img]
