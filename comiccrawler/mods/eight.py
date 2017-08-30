#! python3

"""this is 8comic module for comiccrawler.
	
http://www.comicbus.com/html/197.html

"""

import re
from urllib.parse import urljoin

from node_vm2 import VM

from ..core import Episode, grabhtml, clean_tags

domain = ["www.8comic.com", "www.comicvip.com", "www.comicbus.com"]
name = "無限"

def get_title(html, url):
	return re.search("<title>([^<]+?)漫畫,",html).group(1)

def get_episodes(html, url):
	html = html.replace("\n", "")
	
	js = """
		var output;
		function getCookie() {}
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
				set href(_url) {url = _url; scriptBody()}
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
		jn();
	}
	
	function getImages(url) {
		images = [];
		document.location.href = url;
		return images;
	}
	"""
	
	with VM(js) as vm:
		images = vm.call("getImages", url)
	
	return images
