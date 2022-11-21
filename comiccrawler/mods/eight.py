#! python3

"""this is 8comic module for comiccrawler.
	
http://www.comicbus.com/html/197.html

"""

import re
from urllib.parse import urljoin

from node_vm2 import VM

from ..core import Episode, grabhtml
from ..util import clean_tags
from ..url import update_qs

domain = ["www.8comic.com", "www.comicvip.com", "comicbus.com", "www.comicabc.com"]
name = "無限"
next_page_cache = {}
nview = None

def get_title(html, url):
	return re.search('addhistory\("\d+","([^"]+)',html).group(1)

def get_episodes(html, url):
	html = html.replace("\n", "")
	
	js = """
		var output;
		function getCookie() {}
		function getcookie() {}
		var window = {
			open: function(result){
				output = result;
			}
		};
		var document = {
			location: {
				href: ""
			}
		};
	""" + grabhtml(urljoin(url, "/js/comicview.js"))
	
	s = []
	matches = re.finditer(
		r'<a [^>]*?onclick="(cview[^"]+?);[^>]*>(.+?)</a>',
		html, re.M
	)
	with VM(js) as vm:
		for match in matches:
			cview, title = match.groups()
			
			vm.run(cview)
			ep_url = vm.run("output")
			title = clean_tags(title)

			e = Episode(title, urljoin(url, ep_url))
			s.append(e)
	return s
	
def get_images(html, url):
	global nview
	if not nview:
		nview = re.search('src="([^"]*nview\.js[^"]*)"', html).group(1)
		nview = urljoin(url, nview)
		nview = grabhtml(nview)
	
	try:
		# http://www.comicbus.com/html/103.html
		script = re.search('(var ch=.+?)spp\(\)', html, re.DOTALL).group(1)
	except AttributeError:
		# http://www.comicbus.com/html/7294.html
		script = re.search('(var chs=.+?)</script>', html, re.DOTALL).group(1)
	
	js = """
	var url,
		images = [],
		document = {
			location: {
				toString() {return url;},
				get href() {return url;},
				set href(_url) {url = _url;}
			},
			getElementById() {
				return {
					set src(value) {
						images.push(value);
					},
					style: {}
				};
			}
		},
		navigator = {
			userAgent: "",
			language: ""
		},
		window = {},
		alert = () => {};
		
	function scriptBody() {
		initpage = () => {};
	""" + nview + script + """
		return [images[0], p, ps, ch];
	}
	
	function getImages(url) {
		images = [];
		document.location.href = url;
		return scriptBody();
	}
	"""
	
	with VM(js) as vm:
		img, p, ps, ch = vm.call("getImages", url)
	if p < ps:
		if "/ReadComic/" in url:
			# https://www.comicabc.com/ReadComic/6997/734/734_8d00xI27S.html?p=2
			next_page_cache[url] = update_qs(url, {"p": p + 1})
		else:
			# https://www.comicabc.com/online/new-18117.html?ch=122-2
			next_page_cache[url] = update_qs(url, {"ch": f"{ch}-{p + 1}"})
	

	return urljoin(url, img)

def get_next_page(html, url):
	return next_page_cache.pop(url, None)
