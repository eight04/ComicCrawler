#! python3

import re
from html import unescape
from urllib.parse import urlparse, parse_qs, quote, urljoin

from ..core import Episode
from ..error import PauseDownloadError, SkipEpisodeError

domain = ["chan.sankakucomplex.com"]
name = "Sankaku"
noepfolder = True
config = {
	# curl for chan.sankakucomplex.com
	"curl": "",
	# curl for v.sankakucomplex.com. Note that you should leave this empty.
	"curl_v": ""
}
autocurl = True

def login_check(html):
	if '<a href="/user/login">' in html:
		raise PauseDownloadError("You didn't login")

def get_title(html, url):
	title = re.search(r"<title>/?(.+?) \|", html).group(1)
	return "[sankaku] " + title
	
next_page_cache = {}

def get_episodes(html, url):
	login_check(html)
	s = []
	pid = None
	for m in re.finditer(r'href="(/(?:[^/]*/)?post/show/(\d+))"', html):
		ep_url, pid = m.groups()
		e = Episode(pid, urljoin(url, ep_url))
		s.append(e)
	
	if len(s) > 1:
		# breakpoint()
		tags = parse_qs(urlparse(url).query)["tags"][0]
		tags = quote(tags)
		next_page_cache[url] = f"https://chan.sankakucomplex.com/?tags={tags}&next={pid}"
		
	return s[::-1]

def get_images(html, url):
	if "This post was deleted" in html:
		raise SkipEpisodeError(always=True)
	login_check(html)
	result = ""
	if match := re.search('<a [^>]*highres[^>]*>', html):
		result = re.search('href="([^"]+)"', match.group(0)).group(1)
	elif match := re.search('embed src="([^"]+)"', html):
		result = match.group(1)
	return [urljoin(url, unescape(result))]

def get_next_page(html, url):
	if url in next_page_cache:
		return next_page_cache.pop(url)
		
