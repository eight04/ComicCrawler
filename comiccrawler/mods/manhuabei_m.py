#! python3

"""漫畫唄

https://m.manhuabei.com/manhua/daerwenyouxi/
"""

import re
from html import unescape
from urllib.parse import urljoin

from deno_vm import eval

from ..core import Episode
from ..grabber import grabhtml
from ..util import clean_tags

domain = ["m.manhuabei.com"]
name = "漫畫唄"
no_referer = True

def get_title(html, url):
	return unescape(re.search('<h1[^>]*id="comicName[^>]*>([^<]+)', html).group(1))

def get_episodes(html, url):
	id = re.search("manhua/([^/]+)", url).group(1)
	s = []
	for match in re.finditer(f'<a href="(/manhua/{id}/\d+\.html)"[^>]*>([\s\S]+?)</a', html):
		ep_url, content = match.groups()
		title = clean_tags(content).strip()
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
	(function () {
	
	function atob(data) {
		return Buffer.from(data, "base64").toString("binary");
	}
	
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
	return s;
	
	}).call(global)
	""")
	return images
