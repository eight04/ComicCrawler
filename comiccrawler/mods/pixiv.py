#! python3

"""this is pixiv module for comiccrawler

Ex:
	http://www.pixiv.net/member_illust.php?id=2211832

"""

import re
import json
from html import unescape
from io import BytesIO
from zipfile import ZipFile

from node_vm2 import eval

from ..core import Episode, grabhtml
# from ..error import SkipEpisodeError, PauseDownloadError, is_403
from ..error import PauseDownloadError
from ..url import urljoin

domain = ["www.pixiv.net"]
name = "Pixiv"
noepfolder = True
config = {
	"cookie_PHPSESSID": "請輸入Cookie中的PHPSESSID"
}

def get_title(html, url):
	if ("js-mount-point-search-result-list" not in html and
		"illust_id=" not in url):
		try:
			user = unescape(re.search("class=\"user-name\"[^>]*>([^<]+)", html).group(1))
			id = re.search(r"pixiv.context.userId = \"(\d+)\"", html).group(1)
			return "{} - {}".format(id, user)
		except AttributeError:
			pass
	return "[pixiv] " + unescape(re.search("<title>([^<]+)", html).group(1))
	
def check_login(html):
	if "pixiv.user.loggedIn = true" not in html and "login: 'yes'" not in html:
		raise PauseDownloadError("you didn't login!")	

def get_episodes(html, url):
	check_login(html)
	s = []
	for m in re.finditer(r'<a href="([^"]+)"><h1 class="title" title="([^"]+)">', html):
		ep_url, title = m.groups()
		uid = re.search("id=(\d+)", ep_url).group(1)
		e = Episode("{} - {}".format(uid, unescape(title)), urljoin(url, ep_url))
		s.append(e)
	# search result?
	match = re.search('id="js-mount-point-search-result-list"data-items="([^"]+)', html)
	if match:
		data = unescape(match.group(1))
		for illust in json.loads(data):
			s.append(Episode(
				"{illustId} - {illustTitle}".format_map(illust),
				urljoin(url, "/member_illust.php?mode=medium&illust_id={illustId}".format_map(illust))
			))
			
	# single image
	if "member_illust.php?mode=medium&illust_id" in url:
		s.append(Episode("image", url))
		
	return s[::-1]
	
cache = {}

def get_nth_img(url, i):
	return re.sub(r"_p0(\.\w+)$", r"_p{}\1".format(i), url)

def get_images(html, url):
	check_login(html)
	init_data = re.search(r"(var globalInitData[\s\S]+?)</script>", html).group(1)
	init_data = eval("""
	Object.freeze = null;
	""" + init_data + """
	globalInitData;
	""")
	illust_id = re.search("illust_id=(\d+)", url).group(1)
	illust = init_data["preload"]["illust"][illust_id]
	
	if illust["illustType"] != 2: # normal images
		first_img = illust["urls"]["original"]
		return [get_nth_img(first_img, i) for i in range(illust["pageCount"])]
		
	# https://www.pixiv.net/member_illust.php?mode=medium&illust_id=44298524
	ugoira_meta = "https://www.pixiv.net/ajax/illust/{}/ugoira_meta".format(illust_id)
	ugoira_meta = json.loads(grabhtml(ugoira_meta))
	cache["frames"] = ugoira_meta["body"]["frames"]
	return ugoira_meta["body"]["originalSrc"]

# def errorhandler(er, crawler):
	# http://i1.pixiv.net/img21/img/raven1109/10841650_big_p0.jpg
	# Private page?
	# if is_403(er):
		# raise SkipEpisodeError
			
def imagehandler(ext, bin):
	"""Append index info to ugoku zip"""
	if ext == ".zip":
		bin = pack_ugoira(bin, cache["frames"])
		ext = ".ugoira"
	return ext, bin
	
def pack_ugoira(bin, frames):
	with BytesIO(bin) as imbin:
		with ZipFile(imbin, "a") as zip:
			data = json.dumps({"frames": frames}, separators=(',', ':'))
			zip.writestr("animation.json", data.encode("utf-8"))
		return imbin.getvalue()

def get_next_page(html, url):
	match = re.search("href=\"([^\"]+)\" rel=\"next\"", html)
	if match:
		return urljoin(url, unescape(match.group(1)))
