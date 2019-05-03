#! python3

"""this is pixiv module for comiccrawler

Ex:
	http://www.pixiv.net/member_illust.php?id=2211832

"""

import re
import json
from html import unescape
from io import BytesIO
from urllib.parse import urljoin, urlencode, urlparse, parse_qs
from zipfile import ZipFile

from node_vm2 import eval

from ..core import Episode, grabhtml
from ..error import PauseDownloadError

domain = ["www.pixiv.net"]
name = "Pixiv"
noepfolder = True
config = {
	"cookie_PHPSESSID": "請輸入Cookie中的PHPSESSID"
}

def get_init_data(html):
	js = re.search("(var globalInitData =.+?)</script>", html, re.DOTALL).group(1)
	return eval("""
	Object.freeze = n => n;
	""" + js + """
	globalInitData;
	""")

def get_title_from_init_data(html, url):
	init_data = get_init_data(html)
	user = next(iter(init_data["preload"]["user"].values()))
	tag = get_tag_from_url(url)
	tag = " ({})".format(tag) if tag else ""
	return "{} - {}{}".format(user["userId"], user["name"], tag)

def get_title(html, url):
	if "globalInitData" in html:
		return get_title_from_init_data(html, url)
	return "[pixiv] " + unescape(re.search("<title>([^<]+)", html).group(1))
	
def check_login(data):
	if not data.get("userData"):
		raise PauseDownloadError("you didn't login!")
		
def check_login_html(html):
	if "pixiv.user.loggedIn = true" not in html and "login: 'yes'" not in html:
		raise PauseDownloadError("you didn't login!")
		
cache_next_page = {}

def get_episodes_from_works(works):
	s = []
	for data in sorted(works, key=lambda i: int(i["id"])):
		s.append(Episode(
			"{} - {}".format(data["id"], data["title"]),
			"https://www.pixiv.net/member_illust.php?mode=medium&illust_id={}".format(data["id"])
		))
	return s

def get_tag_from_url(url):
	tags = parse_qs(urlparse(url).query).get("tag")
	return tags[0] if tags else None
		
def get_episodes(html, url):
	if "ajax/user" in url:
		works = json.loads(html)["body"]["works"]
		if isinstance(works, dict):
			works = works.values()
		return get_episodes_from_works(works)

	if "globalInitData" in html:
		init_data = get_init_data(html)
		check_login(init_data)
		
		id = int(next(iter(init_data["preload"]["user"])))
		tag = get_tag_from_url(url)
		
		if tag:
			def build_url(offset):
				query = {
					"offset": str(offset),
					"limit": "48",
					"tag": tag
				}
				return "https://www.pixiv.net/ajax/user/{}/illustmanga/tag?{}".format(id, urlencode(query))
				
			response = grabhtml(build_url(0))
			response = json.loads(response)
			total = response["body"]["total"]
			i = 48
			pre_url = url
			while i < total:
				next_url = build_url(i)
				cache_next_page[pre_url] = next_url
				pre_url = next_url
				i += 48
			return get_episodes_from_works(response["body"]["works"])
		
		all = grabhtml("https://www.pixiv.net/ajax/user/{}/profile/all".format(id))
		all = json.loads(all)
		
		ep_ids = [int(id) for id in list(all["body"]["illusts"]) + list(all["body"]["manga"])]
		ep_ids.sort()
		ep_ids.reverse()
		
		pre_url = url
		for i in range(0, len(ep_ids), 48):
			ids = ep_ids[i:i + 48]
			query = [("ids[]", str(id)) for id in ids] + [("is_manga_top", "0")]
			new_url = "https://www.pixiv.net/ajax/user/{}/profile/illusts?{}".format(
				id, urlencode(query))
			cache_next_page[pre_url] = new_url
			pre_url = new_url
		return []
	
	check_login_html(html)
	s = []
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
	init_data = get_init_data(html)
	check_login(init_data)
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
		
	if url in cache_next_page:
		next_url = cache_next_page[url]
		del cache_next_page[url]
		return next_url		
