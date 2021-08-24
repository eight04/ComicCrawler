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

from ..core import Episode, grabhtml
from ..error import PauseDownloadError, is_http, SkipEpisodeError, SkipPageError
from ..safeprint import print

domain = ["www.pixiv.net"]
name = "Pixiv"
noepfolder = True
config = {
	"cookie_PHPSESSID": "請輸入Cookie中的PHPSESSID"
}

class DataNotFound(Exception):
	pass

def get_init_data(html):
	match = re.search("""meta-global-data" content='([^']+)""", html)
	if not match:
		raise DataNotFound
	data = json.loads(unescape(match.group(1)))
		
	match = re.search("""meta-preload-data" content='([^']+)""", html)
	# if not match:
		# raise DataNotFound
	data["preload"] = json.loads(unescape(match.group(1)))
	
	return data

def get_title_from_init_data(html, url):
	init_data = get_init_data(html)
	user = next(iter(init_data["preload"]["user"].values()))
	tag = get_tag_from_url(url)
	tag = " ({})".format(tag) if tag else ""
	return "{} - {}{}".format(user["userId"], user["name"], tag)
	
def is_search_page(url):
	return re.match("https://www\.pixiv\.net/tags/", url)

def get_title(html, url):
	if is_search_page(url):
		# general title?
		pass
	else:
		try:
			return get_title_from_init_data(html, url)
		except DataNotFound:
			pass
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
	
def get_episodes_from_init_data(html, url):
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
	for page, i in enumerate(range(0, len(ep_ids), 48)):
		ids = ep_ids[i:i + 48]
		query = [("ids[]", str(id)) for id in ids] + [
			("is_manga_top", "0"),
			("work_category", "illustManga"),
			("is_first_page", "1" if page == 0 else "0")
		]
		new_url = "https://www.pixiv.net/ajax/user/{}/profile/illusts?{}".format(
			id, urlencode(query))
		cache_next_page[pre_url] = new_url
		pre_url = new_url
	raise SkipPageError
	
def get_episodes_from_ajax_result(html, url):
	if "ajax/user" not in url:
		raise DataNotFound
	works = json.loads(html)["body"]["works"]
	if isinstance(works, dict):
		works = works.values()
	return get_episodes_from_works(works)
	
def get_episodes_from_search(html, url):
	word = re.search("/tags/([^/]+)", url).group(1)
	query = urlparse(url).query
	# FIXME: is it safe to reuse the query?
	ajax_url = "https://www.pixiv.net/ajax/search/artworks/{}?{}".format(word, query)
	cache_next_page[url] = ajax_url
	raise SkipPageError
	
def is_search_ajax(url):
	return url.startswith("https://www.pixiv.net/ajax/search/artworks/")
	
def get_episodes_from_search_ajax(html, url):
	data = json.loads(html)
	episodes = [
		Episode(
			"{} - {}".format(i["id"], i["title"]),
			"https://www.pixiv.net/artworks/{}".format(i["id"])
		) for i in data["body"]["illustManga"]["data"]
	]
	
	if episodes:
		url_o = urlparse(url)
		query = parse_qs(url_o.query)
		p = query.get("p", ["1"])[0]
		query["p"] = [str(int(p) + 1)]
		cache_next_page[url] = url_o._replace(query=urlencode(query, doseq=True)).geturl()
	
	return episodes[::-1]
		
def get_episodes(html, url):
	if is_search_page(url):
		return get_episodes_from_search(html, url)
		
	if is_search_ajax(url):
		return get_episodes_from_search_ajax(html, url)

	try:
		return get_episodes_from_ajax_result(html, url)
	except DataNotFound:
		pass
		
	try:
		return get_episodes_from_init_data(html, url)
	except DataNotFound:
		pass

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
	if "&amp;" in url:
		# fix bad URL for old saves e.g. 
		# https://www.pixiv.net/member_illust.php?mode=medium&amp;illust_id=12345
		cache_next_page[url] = unescape(url)
		raise SkipPageError

	init_data = get_init_data(html)
	check_login(init_data)
	if len(init_data["preload"]["illust"]) == 1:
		illust_id, illust = init_data["preload"]["illust"].popitem()
	else:
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

def errorhandler(err, crawler):
	if is_http(err, 404):
		url = None
		try:
			url = err.response.url
		except AttributeError:
			pass
		if url and is_ep_url(url):
			# deleted by author?
			# https://www.pixiv.net/member_illust.php?mode=medium&illust_id=68059323
			print("Skip {}: {}".format(err.response.url, 404))
			raise SkipEpisodeError
			
def is_ep_url(url):
	patterns = [
		"member_illust\.php.*illust_id=\d+",
		"/artworks/\d+"
	]
	return any(re.search(p, url) for p in patterns)
			
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
