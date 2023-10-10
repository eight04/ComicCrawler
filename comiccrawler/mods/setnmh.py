#! python3

"""山立？

https://www.setnmh.com/comic-lllop-%E5%B1%B1%E6%B5%B7%E9%80%86%E6%88%B0
"""

import re
import json
from html import unescape
from urllib.parse import urljoin

from deno_vm import eval, VM

from ..core import Episode
from ..grabber import grabhtml

domain = ["www.setnmh.com"]
name = "山立"

def get_title(html, url):
	return unescape(re.search('<h1 class="bookname">([^<]+)', html).group(1))

def get_episodes(html, url):
	cartoon_id = re.search('cartoon_id = "([^"]+)', html).group(1)
	code = grabhtml(
		urljoin(url, "/comicinfo-ajaxgetchapter.html"),
		method = "POST",
		data = {
			"cartoon_id": cartoon_id,
			"order_by": "1",
			"chapter_type": "1"
		},
		header = {
			"X-Requested-With": "XMLHttpRequest"
		}
	)
	# breakpoint()
	ep_data = json.loads(code)
	
	ep_url_code = "var moduleExports = value => " + re.search('href = ("/series-.+)', html).group(1)
	with VM(ep_url_code) as make_url:
		s = []
		for item in ep_data["msg"]:
			sys = item["system"]
			s.append(Episode(
				sys["title"],
				urljoin(url, make_url.call("moduleExports", sys))
			))
	return s[::-1]
	
next_page_cache = {}
	
def get_images(html, url):
	if html[0] == '"':
		# wtf
		html = json.loads(html)
	# breakpoint()
	key = re.search(r'var KEY = "([^"]+)', html).group(1)
	cartoon_id = re.search(r'var CARTOON_ID = "([^"]+)', html).group(1)
	chapter_id = re.search(r'var CHAPTER_ID = "([^"]+)', html).group(1)
	page = re.search(r'var PAGE = "([^"]+)', html).group(1)
	total_page = re.search(r'var TOTAL_PAGE = "([^"]+)', html).group(1)
	
	if int(page) < int(total_page):
		next_page_cache[url] = urljoin(url, re.search('href="([^"]+)">下一頁', html).group(1))

	code = grabhtml(
		urljoin(url, "/comicseries/getpictrue.html"),
		method = "POST",
		data = {
			"key": key,
			"cartoon_id": cartoon_id,
			"chapter_id": chapter_id,
			"page": page
		},
		header = {
			"X-Requested-With": "XMLHttpRequest"
		}
	)
	# breakpoint()
	data = eval(code)
	return data["current"]

def get_next_page(html, url):
	if url in next_page_cache:
		return next_page_cache.pop(url)
	
