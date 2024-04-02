#! python3

"""this is hhxiee module for comiccrawler

Ex:
	http://www.hhxiee.com/comic/1827966/
"""

import re
from urllib.parse import urljoin

from deno_vm import VM

from ..core import Episode, grabhtml

domain = [
	"www.hhxiee.com", "www.hhcomic.cc", "www.hhssee.com", "www.hhmmoo.com",
	"www.hheess.com", "www.1manhua.net"]
name = "汗汗"

def get_title(html, url):
	return re.search("<title>([^<]+)", html).group(1).strip().replace("漫画 - 汗汗漫画", "")
	
def get_episodes(html, url):
	eps = []
	
	for match in re.finditer(r"href='(/page[^>\s']+).+?>([^<]+)", html):
		ep_url, title = match.groups()
		eps.append(Episode(title, urljoin(url, ep_url)))
	return eps[::-1]
	
ctx = None
def build_ctx(url):
	"""Reuse javascript context"""
	global ctx
	js_url = urljoin(url, "/script/view.js")
	js = grabhtml(js_url)
	js = """
		var imgEl = {
				style: {},
				name: ""
			},
			domainEl = {};
			
		const location = {
			href: "",
			hostname: ""
		};
		document = {
			location: location,
			getElementById: function(id){
				if (id == "hdDomain") {
					return domainEl;
				}
				if (/^img/.test(id)) {
					return imgEl;
				}
				return {};
			}
		};
		window = {
			document: document,
			eval: eval,
			parseInt: parseInt,
			String: String,
			RegExp: RegExp
		};
		function getImages(url, name, hdDomain) {
			location.href = url;
			location.hostname = url.match(/:\/\/([^\/]+)/)[1];
			imgEl.name = name;
			domainEl.value = hdDomain;
			
			window_onload();
			return imgEl.src;
		}
	""" + js
	ctx = VM(js).create()
			
def get_images(html, url):
	if not ctx:
		build_ctx(url)
		
	hd_domain = re.search('id="hdDomain" value="([^"]+)', html).group(1)
	img_name = re.search('img[^>]+?name="([^"]+)', html).group(1)
	
	return ctx.call("getImages", url, img_name, hd_domain)
	
def get_next_page(html, url):
	try:
		count = int(re.search('id="hdPageCount" value="([^"]+)', html).group(1))
		current = int(re.search('id="hdPageIndex" value="([^"]+)', html).group(1))
	except AttributeError:
		pass
	else:
		if current < count:
			return re.sub(r"/\d+\.html", "/{}.html".format(current + 1), url)
