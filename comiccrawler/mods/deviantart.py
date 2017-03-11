#! python3

"""this is deviant module for comiccrawler, support deviantart.com

2014/7/13
JDownloader2 now support　deviantart.com!

"""

import re

from html import unescape
from urllib.parse import urljoin

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
	startpos = html.index('id="gmi-ResourceStream"')
	ex = re.compile('<a class="thumb[^"]*?" href="({}/art/.+?)" title="(.+?)"'.format(base))

	for match in ex.finditer(html, startpos):
		id = re.search("\d+$", match.group(1)).group()
		title = match.group(2).rpartition(" by ")[0]
		# WTF r u doing deviantArt?
		title = unescape(unescape(title))

		s.append(
			Episode(
				"{} - {}".format(id, title),
				match.group(1)
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
	next = re.search('id="gmi-GPageButton"[^>]+?href="([^"]+?)"><span>Next</span>', html)
	if next:
		return urljoin(url, unescape(next.group(1)))
