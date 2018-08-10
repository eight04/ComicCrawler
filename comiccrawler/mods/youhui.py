#! python3

"""this is youhui module for comiccrawler

http://m.wuyouhui.net/meishi/shisedalu/
"""

import re
from html import unescape
from urllib.parse import urlparse, urljoin

from ..core import Episode

from .xznj120 import get_images # pylint: disable=unused-import

domain = ["m.wuyouhui.net"]
name = "友繪"

def get_title(html, url):
	match = re.search('<meta property="og:title" content="([^"]+)', html)
	return unescape(match.group(1))

def get_episodes(html, url):
	path = urlparse(url).path
	pattern = '<a href="({}[^"]+)[^>]*?><span>([^<]+)'.format(path)
	s = []
	for match in re.finditer(pattern, html):
		ep_url, ep_title = match.groups()
		s.append(Episode(ep_title, urljoin(url, ep_url)))
	return s[::-1]
