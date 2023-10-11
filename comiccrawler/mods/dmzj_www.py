#! python3
"""
http://www.dmzj.com/info/xixingji.html

"""

import re
from urllib.parse import urljoin

from deno_vm import eval

from ..core import Episode

domain = ["www.dmzj.com"]
name = "動漫之家w"

def get_title(html, url):
	return re.search("comic_name = '([^']+)", html).group(1)

def get_episodes(html, url):
	# dmzj repeat the list twice?...
	end = html.index('<div class="fg"></div>')
	html = html[:end]

	view_url = re.escape(urljoin(url, "/view"))
	pattern = 'href="({view_url}[^"]+)[^>]+?title="([^"]+)'.format(view_url=view_url)
	s = []
	for match in re.finditer(pattern, html):
		ep_url, title = match.groups()
		s.append(Episode(title, ep_url))
	s = s[::-1]
	
	return s

def get_images(html, url):
	# Set base url
	base = "http://images.dmzj.com/"

	# Get urls
	s = re.search(r"page = '';\s+([^\n]+)", html).group(1)
	pages = eval(s + "; pages")
	pages = re.search('"page_url":"([^"]+)', pages).group(1)
	pages = re.split("\r?\n", pages)

	# thumbs.db?!
	# http://manhua.dmzj.com/zhuoyandexiana/3488-20.shtml
	return [base + page for page in pages if page and not page.lower().endswith("thumbs.db")]
