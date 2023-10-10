#! python3

"""吹雪動漫"""

import re
from urllib.parse import urljoin

from deno_vm import eval

from ..core import Episode
from ..grabber import grabhtml

domain = ["www.chuixue.com", "www.chuixue.net"]
name = "吹雪"

def get_title(html, url):
	return re.search("<h1>([^<]+)", html).group(1)

def get_episodes(html, url):
	id = re.search("manhua/(\d+)", url).group(1)
	s = []
	for match in re.finditer('<a href="(/manhua/' + id + '/\d+\.html)"[^>]*>([^<]+)', html):
		ep_url, title = match.groups()
		s.append(Episode(title, urljoin(url, ep_url)))
	return s[::-1]

global_js = None

def get_images(html, url):
	global global_js
	js = re.search("(var ret_classurl.+?)</script>", html, re.DOTALL).group(1)
	if not global_js:
		global_js_url = re.search('src="([^"]+global\.js)"', html).group(1)
		global_js = grabhtml(urljoin(url, global_js_url))
		global_js = re.search("(var WebimgServer.+?)window\.onerror", global_js, re.DOTALL).group(1)
		
	imgs, server = eval("""
	function request() {
		return "";
	}
	""" + js + global_js + """;
	[photosr.slice(1), WebimgServerURL[0]]
	""")
	return [urljoin(server, img) for img in imgs]
