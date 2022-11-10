#! python3

"""this is danbooru module for comiccrawler

Ex:
	https://danbooru.donmai.us/posts?tags=fault!!

"""

import re
from html import unescape
from urllib.parse import urljoin

from ..core import Episode
from ..util import extract_curl
from ..url import urlparse
from ..grabber import get_session

domain = ["danbooru.donmai.us"]
name = "Danbooru"
noepfolder = True
config = {
	"curl": "",
	"curl_cdn": ""
}

def load_config():
	for key, value in config.items():
		if key.startswith("curl") and value:
			url, headers, cookies = extract_curl(value)
			netloc = urlparse(url).netloc
			s = get_session(netloc)
			s.headers.update(headers)
			s.cookies.update(cookies)

def get_title(html, url):
	title = re.search(r"<title>(.+?)</title>", html, re.DOTALL).group(1)
	return title.strip()

def get_episodes(html, url):
	s = []
	for match in re.finditer(r'href="(/posts/(\d+)[^"]*)"', html):
		u = match.group(1)
		title = match.group(2)
		e = Episode(title, urljoin(url, u))
		s.append(e)

	return s[::-1]

def get_images(html, url):
	pos = re.search(r"image-container", html).start()
	img = re.compile(r'data-file-url="([^"]+)"').search(html, pos).group(1)
	return [urljoin(url, img)]

def get_next_page(html, url):
	if re.search("/posts/\d+", url):
		return
		
	m = (re.search(r'<a [^>]*rel="next"[^>]*?href="([^"]+)', html))
	if m:		
		return urljoin(url, unescape(m.group(1)))
