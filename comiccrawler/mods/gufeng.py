#! python3

"""this is gufeng module for comiccrawler

Example:

http://www.gufengmh.com/manhua/jueshiliandanshi/
https://www.gufengmh8.com/manhua/wodedabaojian/
"""

from html import unescape
from urllib.parse import urljoin
import re

from deno_vm import eval

from ..episode import Episode
from ..grabber import grabhtml

domain = ["www.gufengmh.com", "www.gufengmh8.com"]
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
	# http://www.gufengmh.com/js/config.js
	config = grabhtml(urljoin(url, "/js/config.js"))
	return eval("""
	const toastr = {
		options: {}
	};
	""" + config + js + """
	const domain = SinConf.resHost[0].domain[0];
	chapterImages.map(i => `${domain}/${chapterPath}${i}`);
	""")
	
