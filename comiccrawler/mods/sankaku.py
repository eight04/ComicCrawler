#! python3

import re
from html import unescape
from urllib.parse import urljoin

from ..core import Episode
from ..error import PauseDownloadError, SkipEpisodeError, is_http

domain = ["chan.sankakucomplex.com"]
name = "Sankaku"
noepfolder = True
config = {
	# curl for chan.sankakucomplex.com
	"curl": "",
	# curl for v.sankakucomplex.com. Note that you should leave this empty.
	"curl_v": ""
}
no_referer = True
autocurl = True

def after_request(crawler, response):
	if "redirect.png" in response.url:
		raise ValueError("Redirected to chan.sankakucomplex.com")

def is_redirected(err):
	if isinstance(err, ValueError) and "Redirected to chan.sankakucomplex.com" in str(err):
		return True
	if is_http(err) and "redirect" in err.response.url:
		return True
	return False

def errorhandler(err, crawler):
	pass
	# this shouldn't happen without referer
	# if is_redirected(err):
	# 	crawler.init_images()

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

	# FIXME: is there a way to include popular posts without breaking update check?
	# since update check stops if it sees an existing episode
	m = re.search('''id=["']more-popular-link''', html)
	i = m.start() if m else 0 # some query has no popular posts

	for m in re.finditer(r'''href=["']([^"']*posts/([^"']+))''', html[i:]):
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
		
