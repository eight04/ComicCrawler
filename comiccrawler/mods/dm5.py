#! python3

"""this is dm5 module for comiccrawler

Ex:
	http://www.dm5.com/manhua-yaojingdeweiba/
	http://www.dm5.com/manhua-ribenyaoguaidaquan/

"""

import re
from urllib.parse import urljoin

from deno_vm import eval

from ..core import Episode, grabhtml
from ..util import clean_tags
from ..session_manager import session_manager

cookie = {
	"isAdult": "1",
	"fastshow": "true",
	"ComicHistoryitem_zh": "ViewType=1"
}
domain = ["www.dm5.com", "tel.dm5.com", "hk.dm5.com"]
name = "動漫屋"

def load_config():
	s = session_manager.get("https://www.dm5.com/")
	s.headers.update({
		"Accept-Language": "zh-TW,en-US;q=0.7,en;q=0.3"
		})

def get_title(html, url):
	return re.search('DM5_COMIC_MNAME="([^"]+)', html).group(1)

def get_episodes(html, url):
	s = []

	for match in re.finditer(r'<li>\s*<a href="(/m\d+/)"[^>]*>(.+?)</a>', html, re.DOTALL):
		# https://github.com/eight04/ComicCrawler/issues/165
		ep_url, title = match.groups()
		s.append(Episode(
			clean_tags(title),
			urljoin(url, ep_url)
		))
		
	if "DM5_COMIC_SORT=1" in html:
		return s
	return s[::-1]

def get_images(html, url):
	key = re.search(r'id="dm5_key".+?<script[^>]+?>\s*eval(.+?)</script>', html, re.DOTALL)
	
	if key:
		key = eval(key.group(1)).split(";")[1]
		key = re.search(r"=(.+)$", key).group(1)
		key = eval(key)
		
	else:
		key = ""
		
	count = int(re.search(r"DM5_IMAGE_COUNT=(\d+);", html).group(1))
	cid = re.search(r"DM5_CID=(\d+);", html).group(1)
	mid = re.search(r"DM5_MID=(\d+);", html).group(1)
	dt = re.search('DM5_VIEWSIGN_DT="([^"]+)', html).group(1)
	sign = re.search('DM5_VIEWSIGN="([^"]+)', html).group(1)
	
	pages = {}
	
	def grab_page(page):
		params = {
			"cid": cid,
			"page": page + 1,
			"language": 1,
			"key": key,
			"gtk": 6,
			"_cid": cid,
			"_mid": mid,
			"_dt": dt,
			"_sign": sign
		}
		fun_url = urljoin(url, "chapterfun.ashx")
		text = grabhtml(fun_url, referer=url, params=params)
		d = eval(text)
		for i, image in enumerate(d):
			pages[i + page] = image
	
	def create_page_getter(page):
		def getter():
			if page not in pages:
				grab_page(page)
			return pages[page]
		return getter
	
	return [create_page_getter(p) for p in range(count)]
