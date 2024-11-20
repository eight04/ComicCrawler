#! python3

"""oh 漫畫

https://www.ohmanhua.com/13336/
"""

import re
from html import unescape
from urllib.parse import urljoin

from deno_vm import eval

from ..core import Episode, grabhtml

domain = ["www.ohmanhua.com", "www.cocomanhua.com", "www.colamanga.com"]
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
	cdata = re.search("var C_DATA=('[^']+')", html).group(1)
	
	scripts.fetch(html, url, [
		"\/l\.js",
		"common\.js",
		"custom\.js",
		"manga\.read\.js"
	])
	
	code = """
const _log = console.log;

Function.prototype.toString = (function(_toString) {
  return function() {
    return _toString.apply(this, arguments).replace(/\\r?\\n/g, '');
  }
})(Function.prototype.toString);

self.setInterval = function() {};

self.eval = function(_eval) {
  return function() {
    _log('eval', arguments[0]);
    return _eval.apply(this, arguments);
  };
}(self.eval);

self.convertWordArrayToUint8Array =
  self.convertUint8ArrayToWordArray =
  self.__b_a =
  self.__cad = 
  self.__js = 
  undefined;

	(function() {
	
  let _cookies = "";

	function noop(path = "") {
	  if (path === "document.cookie") return _cookies;
	  if (path === "$.inArray") return (v, a) => a.indexOf(v);
	  
	  return new Proxy(() => {}, {
      apply: () => noop(`${path}.called`),
      get: (target, prop) => {
        const propPath = typeof prop == "symbol" ? `${path}.${String(prop)}` : `${path}.${prop}`;
        if (propPath == "document.domain") return "www.colamanga.com";
        _log("get", propPath);
        return noop(propPath);
      },
      set: (target, prop, value) => {
        const propPath = `${path}.${prop}`;
        if (propPath == "document.cookie") {
          _cookies += value.split(";")[0] + "; ";
        }
        _log(propPath, value);
        return value;
      }
	  });
	}

    self.window = self;
	self.location = {
    	protocol: "http://",
		href: '""" + url + """'
	}
	self.navigator = {
	  userAgent: ""
	};
	self.document = noop("document")
	self.$ = noop("$");
    self.devtools = noop("devtools");
	self.localStorage = noop("localStorage");
	
	self.C_DATA = """ + cdata + "\n" + str(scripts) + """
	
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
	}).call(self);
	"""
	
	# import pathlib
	# pathlib.Path("oh0.mjs").write_text(code, encoding="utf-8")
	imgs = eval(code)
	return [urljoin(url, i) for i in imgs]
