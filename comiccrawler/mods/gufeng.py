#! python3

"""this is gufeng module for comiccrawler

Example:

http://www.gufengmh.com/manhua/jueshiliandanshi/
"""

from html import unescape
from urllib.parse import urljoin
import re

from node_vm2 import eval

from ..episode import Episode

domain = ["www.gufengmh.com"]
name = "古風"

def get_title(html, url):
	return unescape(re.search("<h1><span>([^<]+)", html).group(1))

def get_episodes(html, url):
	id = re.search('manhua/([^/]+)', url).group(1)
	pattern = '<a href="(/manhua/{}/\d+.html)"[^>]+?>\s*<span>([^<]+)'.format(id)

	def create_ep(match):
		ep_url, title = [unescape(t) for t in match.groups()]
		return Episode(title, urljoin(url, ep_url))

	return [create_ep(m) for m in re.finditer(pattern, html)]

def get_images(html, url):
	js = re.search('(var siteName.+?)</script>', html, re.DOTALL).group(1)
	return eval(js + """
	// http://www.gufengmh.com/js/config.js
	chapterImages.map(i => `http://res.gufengmh.com/${chapterPath}${i}`);
	""")
	