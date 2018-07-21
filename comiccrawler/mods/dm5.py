#! python3

"""this is dm5 module for comiccrawler

Ex:
	http://www.dm5.com/manhua-yaojingdeweiba/
	http://www.dm5.com/manhua-ribenyaoguaidaquan/

"""

from re import search, finditer, DOTALL
from urllib.parse import urljoin

from node_vm2 import eval

from ..core import Episode, grabhtml

cookie = {
	"isAdult": "1",
	"fastshow": "true",
	"ComicHistoryitem_zh": "ViewType=1"
}
domain = ["www.dm5.com", "tel.dm5.com","hk.dm5.com"]
name = "動漫屋"

def get_title(html, url):
	return search('DM5_COMIC_MNAME="([^"]+)', html).group(1)

def get_episodes(html, url):
	s = []

	for match in finditer('<li>\s*<a href="(/m\d+/)"[^>]*>([^<]+)', html):
		s.append(Episode(
			match.group(2).strip(),
			urljoin(url, match.group(1))
		))

	return s[::-1]

def get_images(html, url):
	key = search(r'id="dm5_key".+?<script[^>]+?>\s*eval(.+?)</script>', html, DOTALL)
	
	if key:
		key = eval(key.group(1)).split(";")[1]
		key = search(r"=(.+)$", key).group(1)
		key = eval(key)
		
	else:
		key = ""
		
	count = int(search("DM5_IMAGE_COUNT=(\d+);", html).group(1))
	cid = search("DM5_CID=(\d+);", html).group(1)
	mid = search("DM5_MID=(\d+);", html).group(1)
	dt = search('DM5_VIEWSIGN_DT="([^"]+)', html).group(1)
	sign = search('DM5_VIEWSIGN="([^"]+)', html).group(1)
	
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
