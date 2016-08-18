#! python3

"""this is yandere module for comiccrawler

Ex:
	https://yande.re/post?tags=koikishi_purely_kiss

"""

import re
from html import unescape
from urllib.parse import urljoin

from ..core import Episode

domain = ["yande.re"]
name = "yande.re"
noepfolder = True

def get_title(html, url):
	title = re.search(r"<title>(.+?)</title>", html, flags=re.DOTALL).group(1)
	title = title.strip("/")
	title = title.replace(" | yande.re", "")
	return "[yande.re] " + title
	
def get_episodes(html, url):
	s = []
	base = re.search("(https?://[^/]+)", url).group(1)
	for match in re.finditer(r'href="(/post/show/(\d+)[^"]*)"', html):
		u = match.group(1)
		title = match.group(2)
		e = Episode(title, base + u)
		s.append(e)
	return s[::-1]
			
def get_images(html, url):
	
	# Original
	img = re.search(
		r'class="original-file-unchanged"[^>]*?href="([^"]+)"',
		html
	)
	
	# Larger version
	if not img:
		img = re.search(r'id="highres" href="([^"]+)"', html)
		
	img = img.group(1)

	return [img]

def get_next_page(html, url):
	u = re.search(r'rel="next" href="([^"]+)"', html)
	if u:
		return urljoin(url, unescape(u.group(1)))
		