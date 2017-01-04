#! python3

"""this is dm5 module for comiccrawler

Ex:
	http://www.dm5.com/manhua-yaojingdeweiba/

"""

from re import search, finditer, DOTALL
from execjs import eval, compile

from urllib.parse import urljoin

from ..core import Episode, grabhtml

cookie = {
	"isAdult": "1",
	"fastshow": "true"
}
domain = ["www.dm5.com", "tel.dm5.com"]
name = "動漫屋"

def get_title(html, url):
	return search('DM5_COMIC_MNAME="([^"]+)', html).group(1)

def get_episodes(html, url):
	s = []
	# base = search("(https?://[^/]+)", url).group(1)
	html = html[html.index("cbc_1"):]

	for match in finditer("class=\"tg\" href=\"([^\"]+)\" title=\"([^\"]+)\"", html):
		s.append(Episode(
			match.group(2),
			urljoin(url, match.group(1))
		))

	return s[::-1]

def create_grabber(fun, url):
	def grabber():
		text = grabhtml(fun, referer=url)
		d = compile(text).eval("(typeof (hd_c) != 'undefined' && hd_c.length > 0 && typeof (isrevtt) != 'undefined') ? hd_c : d")
		return d[0]
	return grabber
	
first_grabber = None
		
def get_images(html, url):
	key = search(r'id="dm5_key".+?<script[^>]+?>\s*eval(.+?)</script>', html, DOTALL)
	
	if key:
		key = eval(key.group(1)).split(";")[1]
		key = search(r"=(.+)$", key).group(1)
		key = eval(key)
		
	else:
		key = ""
		
	count = search("DM5_IMAGE_COUNT=(\d+);", html).group(1)
	cid = search("DM5_CID=(\d+);", html).group(1)
	s = []
	for p in range(1, int(count) + 1):
		fun_url = urljoin(url, "chapterfun.ashx?cid={}&page={}&language=1&key={}&gtk=6".format(cid, p, key))
		s.append(create_grabber(fun_url, url))
		
	global first_grabber
	first_grabber = s[0]
	
	return s

def errorhandler(err, crawler):
	if first_grabber:
		first_grabber()
