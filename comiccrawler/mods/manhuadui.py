#! python3

"""漫畫堆

https://www.manhuadui.com/manhua/huiyedaxiaojiexiangrangwogaobai/
"""

import re
from html import unescape
from urllib.parse import urljoin

from deno_vm import eval

from ..core import Episode
from ..grabber import grabhtml

domain = ["www.manhuadui.com"]
name = "漫畫堆"

def get_title(html, url):
	return unescape(re.search('og:title" content="([^"]+)', html).group(1))

def get_episodes(html, url):
	id = re.search("manhua/([^/]+)", url).group(1)
	s = []
	for match in re.finditer('<a href="(/manhua/' + id + '/\d+\.html)" title="([^"]+)', html):
		ep_url, title = match.groups()
		s.append(Episode(unescape(title), urljoin(url, ep_url)))
	return s
	
class ScriptCache:
	def __init__(self):
		self.cache = {}
		
	def fetch(self, html, url, scripts):
		for script in scripts:
			if script in self.cache:
				continue
			pattern = 'src="([^"]+{})'.format(script)
			js_url = re.search(pattern, html).group(1)
			self.cache[script] = grabhtml(urljoin(url, js_url))
		
	def __str__(self):
		return "\n".join(self.cache.values())
	
scripts = ScriptCache()

def get_images(html, url):
	scripts.fetch(html, url, [
		"crypto-js\.js",
		"decrypt\d+\.js",
		"config\.js",
		"common\.js"
	])
	pre_js = re.search("(var chapterImages.+?)</script>", html, re.DOTALL).group(1)
	main_js = re.search("decrypt\d+\(.+", html).group()
	
	images = eval("""
	function createLocalStorage() {
		const storage = {};
		return {setItem, getItem, removeItem};
		function setItem(key, value) {
			storage[key] = value;
		}
		function getItem(key) {
			return storage[key];
		}
		function removeItem(key) {
			delete storage[key];
		}
	}
	
	const exports = undefined;
	const toastr = {options: {}};
	const top = {
		location: {pathname: ""},
		localStorage: createLocalStorage()
	};
	const jQuery = Object.assign(() => {}, {
		cookie: () => false,
		event: {trigger() {}}
	});
	const $ = jQuery;
	const window = top;
	const SinTheme = {
		initChapter() {},
		getPage() {}
	};
	""" + pre_js + str(scripts) + main_js + """
	const s = [];
	for (let i = 0; i < chapterImages.length; i++) {
		s.push(SinMH.getChapterImage(i + 1));
	}
	s;
	""")
	return images
