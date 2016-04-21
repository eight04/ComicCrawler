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

cookie = {
	"skip_fetish_warning": "1"
}
domain = ["seiga.nicovideo.jp"]
name = "Nico"
noepfolder = True
config = {
	"user_session": "請輸入Cookie中的user_session"
}

def load_config():
	cookie["user_session"] = config["user_session"]

def get_title(html, url):
	artist = re.search(r'nickname">([^<]+)', html).group(1)
	id = re.search(r'data-id="(\d+)', html).group(1)
	return "[Nico] {} - {}".format(id, artist)

def get_episodes(html, url):
	s = []
	for match in re.finditer(r'href="(/seiga/im\d+)">\s*<span[^>]*><img[^>]*?alt="([^"]*)', html):
		ep_url, title = match.groups()
		id = ep_url[7:]
		e = Episode("{} - {}".format(id, unescape(title)), urljoin(url, ep_url))
		s.append(e)
	return s[::-1]

def get_images(html, url):
	if "<!-- ▼Login -->" in html:
		raise PauseDownloadError("You didn't login!")

	source_url = re.search(r'href="(/image/source/\d+)', html)
	if source_url:
		source_html = grabhtml(urljoin(url, source_url.group(1)))
		img = "http://lohas.nicoseiga.jp" + re.search(r'src="(/priv/[^"]+)', source_html).group(1)
		return [img]

	else:
		img = re.search(r'href="(/image/source\?id=\d+)', html).group(1)
		return [urljoin(url, img)]

def get_next_page(html, url):
	match = re.search(r'href="([^"]+)" rel="next"', html)
	if match:
		return urljoin(url, unescape(match.group(1)))
