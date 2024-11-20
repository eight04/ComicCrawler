#! python3

"""this is exh module for comiccrawler, support exhentai.org, g.e-hentai.org

"""

import re

from html import unescape
from urllib.parse import urljoin
from configparser import ConfigParser

from ..episode import Episode
from ..image import Image
from ..util import url_extract_filename
from ..error import PauseDownloadError

domain = ["exhentai.org", "e-hentai.org"]
name = "e紳士"
noepfolder = True
rest = 5
config = {
	"original": "false"
}

def get_boolean(s):
	return ConfigParser.BOOLEAN_STATES.get(s.lower())
	
def check_login(html):
	if html[6:10] == "JFIF" or ("mytags" not in html and "home.php" not in html):
		raise PauseDownloadError("You didn't login!")

def get_title(html, url):
	check_login(html)
	title = re.findall("<h1 id=\"g(j|n)\">(.+?)</h1>", html)[-1][1]
	hash = re.search(r"/g/(\w+/\w+)", url).group(1)
	return unescape("{title} ({hash})".format(title=title, hash=hash))

def get_episodes(html, url):
	check_login(html)
	url = re.search(r'href="([^\"]+?/s/\w+/\w+-1)"', html).group(1)
	e = Episode("image", url)
	return [e]

nl = ""
def get_images(html, url):
	check_login(html)
	global nl
	nl = re.search(r"nl\('([^)]+)'\)", html).group(1)
	
	image = re.search("<img id=\"img\" src=\"(.+?)\"", html)
	image = unescape(image.group(1))
	# bandwith limit
	if re.search(r"509s?\.gif", image) or re.search(r"403s?\.gif", image):
		# pause the download since retry doesn't help but increase view limit.
		raise PauseDownloadError("Bandwidth limit exceeded!")
		
	filename = url_extract_filename(image)

	if get_boolean(config["original"]):
		match = re.search(r'href="([^"]+?/fullimg[^"]+)', html)
		if match:
			image = unescape(match.group(1))

	return Image(image, filename=filename)

def errorhandler(er, crawler):
	url = urljoin(crawler.ep.current_url, "?nl=" + nl)
	if crawler.ep.current_url == url:
		crawler.ep.current_url = url.split("?")[0]
	else:
		crawler.ep.current_url = url
	crawler.html = None

def get_next_page(html, url):
	check_login(html)
	match = re.search('id="next"[^>]+?href="([^"]+)', html)
	if match:
		match = match.group(1)
		if match not in url:
			return match
