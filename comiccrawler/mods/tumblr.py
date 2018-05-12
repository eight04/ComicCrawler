#! python3

"""this is konachan module for tumblr

Example:
	http://otn-pct.tumblr.com/
	https://shonep.tumblr.com/

"""

import re, json
from urllib.parse import urljoin

from ..core import Episode, grabhtml
from ..error import SkipEpisodeError, PauseDownloadError

domain = ["tumblr.com"]
name = "tumblr"
noepfolder = True

config = {
	"full_size": "False",
	"insecure_http": "False",
	"cookie_pfx": "",
	"user_agent": ""
}

header = {}

def load_config():
	header["User-Agent"] = config["user_agent"]

def check_login(html):
	if 'href="https://www.tumblr.com/login"' in html:
		raise PauseDownloadError("You didn't login")

def get_title(html, url):
	title = re.search(r"<title>([^<]+)", html).group(1).strip()
	id = url[url.index("://") + 3: url.index(".tumblr.com")]
	return "[tumblr] {} ({})".format(title, id)
	
def get_episodes(html, url):
	# FIXME: we need a way to check final URL
	check_login(html)
	s = []
	pattern = 'href="(' + re.escape(urljoin(url, "/post/")) + '(\d+)[^"]*)'
	for m in re.finditer(pattern, html):
		url, uid = m.groups()
		s.append(Episode(uid, url))
	return s[::-1]
			
def get_images(html, url):
	images = []
	images.extend(try_get_videos(html, url))
	images.extend(try_get_images(html))
	if not images:
		raise SkipEpisodeError
	return images

def try_get_images(html):
	s = re.search('<script type="application/ld\+json">([^<]*)</script>', html).group(1)
	o = json.loads(s)
	if "image" not in o:
		return
	if isinstance(o["image"], str):
		yield transform(o["image"])
	else:
		yield from (transform(u) for u in o["image"]["@list"])
	
def try_get_videos(html, url):
	match = re.search("<iframe src='(https?://www\.tumblr\.com/video/[^']+)", html)
	if not match:
		return
	frame_src = match.group(1)
	frame_html = grabhtml(frame_src, referer=url)
	source_src = re.search('<source src="([^"]+)', frame_html).group(1)
	source_src = re.sub("/\d+$", "", source_src)
	yield source_src
	
def transform(url):
	"""Map thumbnail to full size"""
	# https://github.com/eight04/ComicCrawler/issues/82
	if config.getboolean("full_size"):
		url = re.sub("[^/]+\.tumblr\.com", "data.tumblr.com", url)
		url = re.sub("_\d+(\.\w+)$", r"_raw\1", url)
	if config.getboolean("insecure_http"):
		url = re.sub("^https:", "http:", url)
	return url

def get_next_page(html, url):
	match = re.search(r'/page/(\d+)', url)
	if match:
		page = int(match.group(1))
	else:
		page = 1
	
	next_url = "/page/{page}".format(page=page + 1)
	
	if next_url in html:
		return urljoin(url, next_url)
