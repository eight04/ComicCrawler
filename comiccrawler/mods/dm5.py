#! python3

"""this is dm5 module for comiccrawler

Ex:
	http://www.dm5.com/manhua-yaojingdeweiba/

"""

from re import search, finditer, DOTALL
from execjs import eval, compile

from urllib.parse import urljoin

from ..core import Episode, grabhtml
from ..safeprint import safeprint
from ..error import LastPageError

header = {
	"Cookie": "isAdult=1"
}
domain = ["www.dm5.com", "tel.dm5.com"]
name = "動漫屋"

def gettitle(html, url):
	return search("class=\"inbt_title_h2\">([^<]+)</h1>", html).group(1)

def getepisodelist(html, url):
	s = []
	# base = search("(https?://[^/]+)", url).group(1)
	html = html[html.index("cbc_1"):]

	for match in finditer("class=\"tg\" href=\"([^\"]+)\" title=\"([^\"]+)\"", html):
		s.append(Episode(
			match.group(2),
			urljoin(url, match.group(1))
		))

	return s[::-1]

cache = {}
def getimgurl(html, url, page):
	if url not in cache:
		key = search(r'id="dm5_key".+?<script[^>]+?>\s*eval(.+?)</script>', html, DOTALL)
		if key:
			key = eval(key.group(1)).split(";")[1]
			key = search(r"=(.+)$", key).group(1)
			key = eval(key)
		else:
			key = ""
		length = search("DM5_IMAGE_COUNT=(\d+);", html).group(1)
		cid = search("DM5_CID=(\d+);", html).group(1)
		funs = []
		for p in range(1, int(length) + 1):
			fun_url = urljoin(url, "chapterfun.ashx?cid={}&page={}&language=1&key={}&gtk=6".format(cid, p, key))
			funs.append(fun_url)
		cache[url] = funs

	if page - 1 >= len(cache[url]):
		del cache[url]
		raise LastPageError

	fun_url = cache[url][page - 1]
	text = grabhtml(fun_url, referer=url)
	d = compile(text).eval("(typeof (hd_c) != 'undefined' && hd_c.length > 0 && typeof (isrevtt) != 'undefined') ? hd_c : d")
	return d[0]

def getnextpageurl(html, url, page):
	return url
