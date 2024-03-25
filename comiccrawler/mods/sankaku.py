#! python3

import re
from html import unescape
from urllib.parse import urljoin

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

def after_request(crawler, response):
	if "redirect.png" in response.url:
		crawler.init_images()
		raise ValueError("Redirected to chan.sankakucomplex.com")

def valid_id(pid):
	if pid in ["upload", "update"]:
		return False
	return True

def login_check(html):
	match = re.search(r"'setUserId', '([^']+')", html)
	if not match:
		raise PauseDownloadError("Not logged in")

def get_title(html, url):
	title = re.search(r"<title>/?(.+?) \|", html).group(1)
	return "[sankaku] " + unescape(title)
	
def get_episodes(html, url):
	login_check(html)
	s = []

	for m in re.finditer(r'href="([^"]*posts/([^"]+))', html):
		ep_url, pid = m.groups()
		if not valid_id(pid):
			continue
		e = Episode(pid, urljoin(url, ep_url))
		s.append(e)
	
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
	match = re.search('next-page-url="([^"]+)"', html)
	if match:
		u = unescape(unescape(match.group(1)))
		return urljoin(url, u)

def get_next_image_page(html, url):
	pass
		
