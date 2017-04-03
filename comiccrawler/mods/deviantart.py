#! python3

"""this is deviant module for comiccrawler, support deviantart.com

2014/7/13
JDownloader2 now support　deviantart.com!

"""

import re

from html import unescape
from urllib.parse import urljoin, urlparse, urlunparse, parse_qs, urlencode

from ..error import PauseDownloadError
from ..core import Episode

domain = ["deviantart.com"]
name = "dA"
noepfolder = True
config = {
	"cookie_auth": "請輸入Cookie中的auth",
	"cookie_userinfo": "請輸入Cookie中的userinfo"
}

def get_title(html, url):
	return unescape(re.search("<title>(.+?)</title>", html).group(1))
	
def check_login(html, url):
	if not re.search('"loggedin":true', html, re.I):
		raise PauseDownloadError("you didn't log in!")

def get_episodes(html, url):
	check_login(html, url)
	
	base = re.search("(https?://[^/]+)", url).group(1)
	s = []
	pattern = '<a class="torpedo-thumb-link" href="({}/art/[^"]+?(\d+))".+?class="title">([^<]*)'.format(base)

	for match in re.finditer(pattern, html, re.DOTALL):
		ep_url, id, title = match.groups()
		# WTF r u doing deviantArt?
		title = unescape(unescape(title))

		s.append(
			Episode(
				"{} - {}".format(id, title),
				ep_url
			)
		)

	return s[::-1]

def get_images(html, url):
	check_login(html, url)

	html = html.replace("\n", "")
	try:
		i = re.search('dev-page-download"\s+href="([^"]+)"', html).group(1)
		return [unescape(i)]
	except AttributeError:
		pass
	i = re.search('<img[^>]+?src="([^"]+)"[^>]+?class="dev-content-full[^"]*">', html).group(1)
	return [i]
	
def get_next_page(html, url):
	if '"hasMore":true' not in html:
		return None
	next_offset = re.search('"nextOffset":(\d+)', html).group(1)
	return apply_query(url, {"offset": next_offset})
	
def apply_query(url, new_query):
	scheme, netloc, path, params, query, fragment = urlparse(url)
	query_dict = parse_qs(query)
	query_dict.update(new_query)
	query = urlencode(query_dict, doseq=True)
	return urlunparse((scheme, netloc, path, params, query, fragment))
