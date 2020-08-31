#! python3

"""this is nico seiga module for comiccrawler

Ex:
	http://seiga.nicovideo.jp/user/illust/11937543?target=illust_all

"""

import re

from html import unescape

from urllib.parse import urljoin

from ..core import Episode, grabhtml
from ..error import PauseDownloadError

cookie = {
	"skip_fetish_warning": "1"
}
domain = ["seiga.nicovideo.jp"]
name = "Nico"
noepfolder = True
config = {
	"cookie_user_session": "請輸入Cookie中的user_session"
}

def get_title(html, url):
	if "/user/" in url:
		artist = re.search(r'nickname">([^<]+)', html).group(1)
		id = re.search(r'data-id="(\d+)', html).group(1)
		return "[Nico] {} - {}".format(id, artist)
		
	title = re.search("<title>([^<]+)", html).group(1).partition(" - ")[0]
	return "[Nico] {}".format(title)

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
		# FIXME: The image is downloaded twice within redirect!
		source_url = urljoin(url, source_url.group(1))
		source_html = grabhtml(source_url)
		image = re.search(r'data-src="([^"]+)', source_html)
		if image:
			image = image.group(1)
		else:
			image = source_url
		return [image]

	img = re.search(r'href="(/image/source\?id=\d+)', html).group(1)
	return [urljoin(url, img)]

def get_next_page(html, url):
	match = re.search(r'href="([^"]+)" rel="next"', html)
	if match:
		return urljoin(url, unescape(match.group(1)))
