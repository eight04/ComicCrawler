#! python3

import re
from html import unescape
from urllib.parse import urljoin

from ..core import Episode
from ..error import PauseDownloadError

domain = ["chan.sankakucomplex.com"]
name = "Sankaku"
noepfolder = True
config = {
	"cookie_cf_clearance": "Set cf_clearance",
	"cookie__sankakucomplex_session": "Set _sankakucomplex_session",
	"cookie_pass_hash": "Set pass_hash",
	"cookie_login": "Set login"
}

def login_check(html):
	if '<a href="/user/login">' in html:
		raise PauseDownloadError("You didn't login")

def get_title(html, url):
	title = re.search(r"<title>/?(.+?) \|", html).group(1)
	return "[sankaku] " + title

def get_episodes(html, url):
	login_check(html)
	s = []
	base = re.search("(https?://[^/]+)", url).group(1)
	for m in re.finditer(r'href="(/(?:[^/]*/)?post/show/(\d+))"', html):
		url, pid = m.groups()
		e = Episode(pid, base + url)
		s.append(e)
	return s[::-1]

def get_images(html, url):
	login_check(html)
	u = re.search('href="([^"]+)" id=highres', html)
	if not u:
		u = re.search('embed src="([^"]+)"', html)
	return ["https:" + u.group(1)]

def get_next_page(html, url):
	match = re.search('next-page-url="([^"]+)"', html)
	if match:
		return urljoin(url, unescape(match.group(1)))
		