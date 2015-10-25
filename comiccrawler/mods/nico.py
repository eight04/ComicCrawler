#! python3

"""this is nico seiga module for comiccrawler

Ex:
	http://seiga.nicovideo.jp/user/illust/11937543?target=illust_all

"""

import re, execjs
from html import unescape
from urllib.error import HTTPError
from urllib.parse import urljoin

from ..core import Episode, grabhtml
from ..error import LastPageError, SkipEpisodeError, PauseDownloadError
from ..safeprint import safeprint

cookie = {
	"skip_fetish_warning": "1"
}
domain = ["seiga.nicovideo.jp"]
name = "Nico"
noepfolder = True
config = {
	"user_session": "請輸入Cookie中的user_session"
}

def loadconfig():
	cookie.update(config)

def gettitle(html, url):
	artist = re.search(r'nickname">([^<]+)', html).group(1)
	id = re.search(r'data-id="(\d+)', html).group(1)
	return "{} - {}".format(id, artist)

def getepisodelist(html, url):
	s = []
	while True:
		for match in re.finditer(r'href="(/seiga/im\d+)">\s*<span[^>]*><img[^>]*?alt="([^"]*)', html):
			ep_url, title = m.groups()
			id = ep_url[7:]
			e = Episode("{} - {}".format(id, unescape(title)), urljoin(url, ep_url))
			s.append(e)

		next_url = re.search(r'href="([^"]+)" rel="next"', html)
		if next_url is None:
			break
		next_url = urljoin(url, unescape(next_url.group(1)))
		safeprint(next_url)
		html = grabhtml(next_url)
	return s[::-1]

def getimgurls(html, url):
	source_url = re.search(r'href="(/image/source/\d+)', html)
	if source_url:
		source_html = grabhtml(source_url.group(1))
		img = re.search(r'src="(/priv/[^"]+)').group(1)
	else:
		img = re.search(r'href="(/image/source?id=\d+)', html).group(1)
	return [urljoin(url, img)]

def errorhandler(er, ep):
	pass
