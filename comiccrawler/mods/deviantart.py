#! python3

"""this is deviant module for comiccrawler, support deviantart.com

2014/7/13
JDownloader2 now support　deviantart.com!

"""

from re import search, compile
from html import unescape
from urllib.parse import urljoin

from ..safeprint import safeprint
from ..error import PauseDownloadError
from ..core import Episode, grabhtml

cookie = {}
domain = ["deviantart.com"]
name = "dA"
noepfolder = True
config = {
	"auth": "請輸入Cookie中的auth",
	"userinfo": "請輸入Cookie中的userinfo"
}

def load_config():
	cookie.update(config)

def get_title(html, url):
	return unescape(search("<title>(.+?)</title>", html).group(1))

def get_episodes(html, url):
	if '"loggedIn":true' not in html:
		raise PauseDownloadError("you didn't log in!")
	base = search("(https?://[^/]+)", url).group(1)
	s = []
	startpos = html.index('id="gmi-ResourceStream"')
	ex = compile('<a class="thumb[^"]*?" href="({}/art/.+?)" title="(.+?)"'.format(base))

	for match in ex.finditer(html, startpos):
		id = search("\d+$", match.group(1)).group()
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
	if '"loggedIn":true' not in html:
		raise PauseDownloadError("you didn't log in!")

	html = html.replace("\n", "")
	try:
		i = search('dev-page-download"\s+href="([^"]+)"', html).group(1)
		return [unescape(i)]
	except Exception:
		pass
	i = search('<img[^>]+src="([^"]+)"[^>]+class="dev-content-full">', html).group(1)
	return [i]
	
def get_next_page(html, url):
	next = search('id="gmi-GPageButton"[^>]+?href="([^"]+?)"><span>Next</span>', html)
	if next:
		return urljoin(url, unescape(next.group(1)))
