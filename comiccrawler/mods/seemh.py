#! python3

"""
http://tw.manhuagui.com/comic/25713/
http://tw.manhuagui.com/comic/25713/351280.html#p=1
"""

import re
from itertools import cycle
from urllib.parse import urljoin, urlencode

from node_vm2 import VM, eval

from ..core import Episode, grabhtml

domain = ["seemh.com", "ikanman.com", "manhuagui.com"]
name = "看漫畫"
config = {
	"nowebp": "False"
}
grabber_cooldown = {
	"www.manhuagui.com": 3,
	"tw.manhuagui.com": 3
}

def get_title(html, url):
	return re.search(r'<h1>([^<]*)', html).group(1)

def get_list(html, cid):
	ep_re = r'href="(/comic/{}/\d+\.html)" title="([^"]+)"'.format(cid)
	arr = []
	try:
		comment_pos = html.index('class="comment-bar"')
	except ValueError:
		comment_pos = len(html)

	for match in re.finditer(ep_re, html):
		if match.start() >= comment_pos:
			break
		ep_url, title = match.groups()
		arr.append((title, ep_url))
	return arr


def get_episodes(html, url):
	episodes = None
	cid = re.search(r"comic/(\d+)", url).group(1)
	
	# http://tw.ikanman.com/comic/10924/
	episodes = get_list(html, cid)
	
	# http://tw.ikanman.com/comic/4350/
	if not episodes:
		view_state = re.search(
			r'id="__VIEWSTATE" value="([^"]+)', html).group(1)
		js_main = re.search(r'src="([^"]+?/main_[^"]*?\.js)"', html).group(1)
		js_main = grabhtml(js_main)
		js_main = re.search(r'^window\[.+', js_main, re.M).group()
		js = """
			var window = global;
		""" + js_main
		
		with VM(js) as vm:
			ep_html = vm.call("LZString.decompressFromBase64", view_state)
			
		episodes = get_list(ep_html, cid)
		
	episodes = [Episode(v[0].strip(), urljoin(url, v[1])) for v in episodes]
	return episodes[::-1]
	
servers = None

def get_images(html, url):
	# build js context
	js = """
	var window = global;
	var cInfo;
	var SMH = {
		imgData: function(data) {
			cInfo = data;
			return {
				preInit: function(){}
			};
		}
	};
	"""
	
	configjs_url = re.search(
		r'src="(https?://[^"]+?/config_\w+?\.js)"',
		html
	).group(1)
	configjs = grabhtml(configjs_url, referer=url)
	js += re.search(
		r'^(var CryptoJS|window\["\\x65\\x76\\x61\\x6c"\]).+',
		configjs,
		re.MULTILINE
	).group()

	js += re.search(
		r'<script type="text/javascript">((eval|window\["\\x65\\x76\\x61\\x6c"\]).+?)</script',
		html
	).group(1)
	
	with VM(js) as vm:
		files, path, md5, cid = vm.run("[cInfo.files, cInfo.path, cInfo.sl.md5, cInfo.cid]")
	
	# find server
	# "http://c.3qfm.com/scripts/core_5C348B32A78647FF4208EACA42FC5F84.js"
	# getpath()
	corejs_url = re.search(
		r'src="(https?://[^"]+?/core_\w+?\.js)"',
		html
	).group(1)
	corejs = grabhtml(corejs_url, referer=url)
	
	# cache server list
	servs = re.search(r"var servs=(.+?),pfuncs=", corejs).group(1)
	servs = eval(servs)
	servs = [host["h"] for category in servs for host in category["hosts"]]
	
	global servers
	servers = cycle(servs)

	host = next(servers)
	
	utils = re.search(r"SMH\.(utils=.+?),SMH\.imgData=", corejs).group(1)
	
	js = """
	var location = {
		protocol: "http:"
	};
	""" + utils + """;
	function getFiles(path, files, host) {
		// lets try if it will be faster in javascript
		return files.map(function(file){
			return utils.getPath(host, path + file);
		});
	}
	"""
	with VM(js) as vm:
		images = vm.call("getFiles", path, files, host)
	
	if config.getboolean("nowebp"):
		images = map(lambda i: i[:-5] if i.endswith(".webp") else i, images)
		
	params = urlencode({
		"cid": cid,
		"md5": md5
	})
	images = ["{file}?{params}".format(file=i, params=params) for i in images]
	
	return images
	
def errorhandler(err, crawler):
	"""Change host"""
	if crawler.image and crawler.image.url:
		host = next(servers)
		crawler.image.url = re.sub(
			r"://.+?\.",
			"://{host}.".format(host=host),
			crawler.image.url
		)
