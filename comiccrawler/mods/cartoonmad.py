#! python3

"""動漫狂"""

import re

from urllib.parse import urljoin

from ..core import Episode

domain = ["www.cartoonmad.com"]
name = "動漫狂"

def get_title(html, url):
	return re.search("<title>([^<]+) - [^<]+? - [^<]+<", html).group(1)

def get_episodes(html, url):
	s = []
	for match in re.finditer('href=(/comic/\d{6,}[^\s>]+).*?>([^<]+)', html):
		ep_url, title = match.groups()
		s.append(Episode(title, urljoin(url, ep_url)))
	return s

def get_images(html, url):
	pic_url = re.search(r'img src="([^"]*(comicpic|cc\.fun8\.us)[^"]+)', html).group(1)
	return urljoin(url, pic_url)
	
def get_next_page(html, url):
	match = re.search('a href="(\d+[^"]*)', html)
	if match:
		return urljoin(url, match.group(1))
