#! python3
# fmt: off

"""colamanga

E.g. Zombie World
https://www.colamanga.com/manga-mr87910/
"""

import re
from html import unescape

# import time
from urllib.parse import urljoin

from Cryptodome.Cipher import AES
from deno_vm import VM

from ..core import Episode, grabhtml
from ..session_manager import session_manager

domain = ["www.colamanga.com"]
name = "colamanga"


def load_config():
	session = session_manager.get("https://img.colamanga.com")
	session.headers.update(
		{
			"accept": "*/*",
			"accept-language": "en-US,en;q=0.9",
			"origin": "https://www.colamanga.com",
		}
	)


def get_title(html, url):
	title = re.search(
		'meta property="og:comic:book_name" content="([^"]+)', html
	).group(1)
	return unescape(title).strip()


def get_episodes(html, url):
	s = []
	for match in re.finditer(r'title="([^"]+)" href="([^"]+)', html):
		title, ep_url = match.groups()
		s.append(Episode(unescape(title), urljoin(url, ep_url)))
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

	def __getitem__(self, script):
		return self.cache[script]

	def __str__(self):
		return "\n".join(self.cache.values())


scripts = ScriptCache()
# NOTE: global dictionary don't need `global` keyword
data = {}


def get_images(html, url):
	cdata = re.search("var C_DATA=('[^']+')", html).group(1)

	scripts.fetch(
		html, url, scripts=[r"\/l\.js", r"common\.js", r"custom\.js", r"manga\.read\.js"]
	)

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
			[mh_info.pageid]: {
				use_line: mh_info.domain
			}
		};
		window.chapter_id = mh_info.pageid;

		// const imgs = [];
		// let dirty = false;
		// class Image {
		// set src(val) {
		//	  imgs.push(val);
		//	  dirty = true;
		//	 }
		// }
		// let i = mh_info.startimg;
		// do {
		//	  dirty = false;
		//	  __cr.preLoadImg(i++)
		// } while (dirty);

		__cad.setCookieValue();
		// const _tka_pageid = __cad.cookie(__cad.getCookieValue()[0] + mh_info.pageid.toString());
		// const _tkb_pageid = __cad.cookie(__cad.getCookieValue()[1] + mh_info.pageid.toString());
		const len = __cad.cookie(__cad.getCookieValue()[1] + mh_info.pageid.toString());

		const imgs = [];
		for (let i = mh_info.startimg; i <= len; ++i) {
			imgs.push(__cr.getPicUrl(i));
		}
		const keyTypes = image_info.keyType
		let key;

		if (keyTypes == 0) {
			__cr.isfromMangaRead = 1;
			key =  __js.getDataParse();
		}

		self.getKey = (fn, index) => {
			const hexKey = eval(`${fn}(${index})`);
			return CryptoJS.enc.Utf8.parse(hexKey);
		}

		return [imgs, key, keyTypes]
	}).call(self);
	"""

	with VM() as vm:
		imgs, key, key_types = vm.run(code)

		if not key:
			key_pairs = re.findall(r"if\(_0x[0-9a-f]{6}==(0x[0-9a-f]{4,})\)return _0x[0-9a-f]{6}\((0x[0-9a-f]+)\)", scripts[r"manga\.read\.js"])

			pair = next((t for t in key_pairs if hex(int(key_types)) in t), None)
			if pair is None:
				raise ValueError("Key pair not found!")
			index = pair[1]

			fn_name = re.search(r"function (_0x[0-9a-f]{4})\(_0x[0-9a-f]{6},_0x[0-9a-f]{6}\)", scripts[r"manga\.read\.js"]).group(1)

			key = vm.call("getKey", fn_name, index)

	data["key"] = key

	return [urljoin(url, i) for i in imgs]


def imagehandler(ext, bin):
	if ext == ".webp":
		key = data["key"]

		if not key:
			raise ValueError("Key not found!")

		key_bytes = b"".join(list(i.to_bytes(4, "big") for i in key["words"]))
		cipher = AES.new(key_bytes, mode=AES.MODE_CBC, iv=b"0000000000000000")
		bin = cipher.decrypt(bytes(bin))
	return ext, bin

