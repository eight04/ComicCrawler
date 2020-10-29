#! python3

"""oh 漫畫

https://www.ohmanhua.com/13336/
"""

import re
from html import unescape
from urllib.parse import urljoin

from node_vm2 import eval

from ..core import Episode, grabhtml

domain = ["www.ohmanhua.com", "www.cocomanhua.com"]
name = "OH漫畫"

def get_title(html, url):
	title = re.search('meta property="og:comic:book_name" content="([^"]+)', html).group(1)
	return unescape(title).strip()

def get_episodes(html, url):
	s = []
	for match in re.finditer(r'title="([^"]+)" href="([^"]+)', html):
		title, ep_url = match.groups()
		s.append(Episode(
			unescape(title),
			urljoin(url, ep_url)
		))
	return s[::-1]

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
	cdata = re.search("var C_DATA='[^']+'", html).group(0)
	
	scripts.fetch(html, url, [
		"\/l\.js",
		"common\.js",
		"custom\.js",
		"manga\.read\.js"
	])
	
	code = """
	(function() {
	
	function noop(path = "") {
	  if (path === "document.cookie") return "";
	  if (path === "$.inArray") return (v, a) => a.indexOf(v);
	  
	  return new Proxy(() => {}, {
		apply: () => noop("?"),
		get: (target, prop) => noop(`${path}.${prop}`)
	  });
	}
	
	const exports = undefined;
	const window = global;
	window.location = {
    	protocol: "http://",
		href: '""" + url + """'
	}
	const navigator = {
	  userAgent: ""
	};
	const document = noop("document")
	const $ = noop("$");
	
	""" + cdata + "\n" + str(scripts) + """
	
	window.use_domain = {
	},
	window.lines = {
	  [mh_info.chapter_id]: {
		use_line: mh_info.domain
	  }
	};
	window.chapter_id = mh_info.chapter_id;
	
	const imgs = [];
	let dirty = false;
	class Image {
		set src(val) {
			imgs.push(val);
			dirty = true;
		}
	}
	
	let i = mh_info.startimg;
	do {
		dirty = false;
		__cr.preLoadImg(i++)
	} while (dirty);
	return imgs;
	}).call(global);
	"""
	
	imgs = eval(code)
	return [urljoin(url, i) for i in imgs]
