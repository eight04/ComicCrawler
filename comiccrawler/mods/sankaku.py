#! python3

import re
from html import unescape
from urllib.parse import urljoin

from ..core import Episode, grabhtml
from ..safeprint import safeprint

cookie = {}
domain = ["chan.sankakucomplex.com"]
name = "Sankaku"
noepfolder = True
config = {
	"cf_clearance": "請輸入Cookie中的cf_clearance"
}

def load_config():
	cookie.update(config)

def get_title(html, url):
	title = re.search(r"<title>/?(.+?) \|", html).group(1)
	return "[sankaku] " + title

def get_episodes(html, url):
	s = []
	base = re.search("(https?://[^/]+)", url).group(1)
	for m in re.finditer(r'href="(/(?:[^/]*/)?post/show/(\d+))"', html):
		url, pid = m.groups()
		e = Episode(pid, base + url)
		s.append(e)
	return s[::-1]

def get_images(html, url):
	u = re.search('href="([^"]+)" id=highres', html)
	if not u:
		u = re.search('embed src="([^"]+)"', html)
	return ["https:" + u.group(1)]

def get_next_page(html, url):
	match = re.search('next-page-url="([^"]+)"', html)
	if match:
		return urljoin(url, unescape(match.group(1)))
		