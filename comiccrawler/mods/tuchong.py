#! python3

"""this is tuchong module for comiccrawler

Ex:
	https://tuchong.com/\d+/

"""

import re

from ..core import Episode

domain = ["tuchong.com"]
name = "圖蟲"

def get_title(html, url):
	author = re.search('meta name="author" content="([^"]+)', html).group(1)
	id = re.search('tuchong\.com/(\d+)', url).group(1)
	return "[圖蟲] {author} ({id})".format(author=author, id=id)

def get_episodes(html, url):
	s = []

	for match in re.finditer('href="([^"]+?tuchong\.com/\d+/(\d+)[^"]*)" title="([^"]+)', html):
		ep_url, ep_id, title = match.groups()
		title = "{id} - {title}".format(id=ep_id, title=title)
		s.append(Episode(title, ep_url))

	return s[::-1]

def get_images(html, url):
	return re.findall('<img src="([^"]+?photo\.tuchong\.com[^"]+)', html)
