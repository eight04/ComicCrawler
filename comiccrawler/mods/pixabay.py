#! python3

"""
https://pixabay.com/users/kellepics-4893063/
"""

import re
from html import unescape
from urllib.parse import urljoin

from ..episode import Episode

domain = ["pixabay.com"]
name = "pixabay"
noepfolder = True
config = {
	"cookie_sessionid": ""
}

def get_title(html, url):
	title = re.search("<h1[^>]*>([^<]+)", html).group(1)
	return "[pixabay] {}".format(unescape(title))
	
def get_episodes(html, url):
	pattern = '<a href="(/\w+/[\w-]+-(\d+)/)".+?(?:src|data-lazy)="[^"]+/([\w-]+\d+)__\d+(\.[\w]+)" alt="([^"]+)'
	s = []
	for match in re.finditer(pattern, html):
		ep_url, id, name, ext, alt = match.groups()
		title = "{} - {}".format(id, alt)
		ep = Episode(
			title=title,
			url=urljoin(url, ep_url),
			image="https://pixabay.com/images/download/{}{}?attachment".format(name, ext)
		)
		s.append(ep)
	return s[::-1]

def get_next_page(html, url):
	match = re.search('<a class="[^"]*?next" href="([^"]+)', html)
	if match:
		return urljoin(url, match.group(1))
