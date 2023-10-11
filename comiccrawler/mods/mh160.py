#! python3

"""this is mh160 module for comiccrawler

https://www.mh160.com/kanmanhua/30526/
"""

import re
from html import unescape
from urllib.parse import urlparse, urljoin
from deno_vm import eval

from ..core import Episode
from ..grabber import grabhtml

domain = ["www.mh160.com"]
name = "160"

def get_title(html, url):
	match = re.search('<meta property="og:title" content="([^"]+)', html)
	return unescape(match.group(1))

def get_episodes(html, url):
	path = urlparse(url).path
	pattern = '<a href="({}[^"]+)" title="([^"]+)'.format(path)
	s = []
	for match in re.finditer(pattern, html):
		ep_url, ep_title = match.groups()
		s.append(Episode(unescape(ep_title), urljoin(url, ep_url)))
	return s[::-1]
	
def get_images(html, url):
	js_url = re.search(r'src="([^"]+base64\.js)"', html).group(1)
	js_content = grabhtml(urljoin(url, js_url))
	data = re.search('(var chapterTree=.+?)</script>', html, re.DOTALL).group(1)
	match = re.search(r'window\["\\x65\\x76\\x61\\x6c"\](.+?)</script>', html, re.DOTALL)
	data2 = match.group(1) if match else ""

	imgs = eval("""
	const document = {{}};
	{};
	{};
	eval({});
	getUrlpics().map(getrealurl);
	""".format(js_content, data, data2))
	
	return imgs
