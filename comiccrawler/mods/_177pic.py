#! python3

"""
http://www.177pic.info/html/2019/09/3114079.html
"""

import re
from html import unescape

from ..core import Episode

domain = ["www.177pic.info"]
name = "177"
noepfolder = True

def get_title(html, url):
	title = re.search(r'<h1[^>]*>([^<]+)', html).group(1)
	return unescape(title).strip()

def get_episodes(html, url):
	return [Episode("image", url)]

def get_images(html, url):
	imgs = []
	for match in re.finditer(r'data-lazy-src="([^"]+)', html):
		imgs.append(match.group(1))
	return imgs
	
def get_next_page(html, url):
	next_page = re.search(r'href="([^"]+)"><span><i class="be be-arrowright">', html)
	if next_page:
		return next_page.group(1)
