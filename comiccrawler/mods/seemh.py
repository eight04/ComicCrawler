#! python3

"""
http://tw.manhuagui.com/comic/25713/
http://tw.manhuagui.com/comic/25713/351280.html#p=1
"""

import re
from itertools import cycle
from urllib.parse import urljoin, urlencode

from deno_vm import VM, eval

from ..core import Episode, grabhtml
from ..util import balance

domain = ["seemh.com", "ikanman.com", "manhuagui.com", "www.mhgui.com"]
name = "看漫畫"
config = {
	"nowebp": "False"
}
grabber_cooldown = {
	"www.manhuagui.com": 3,
	"tw.manhuagui.com": 3
}
header = {
	"Accept-Language": "zh-tw,zh;q=0.8,en-us;q=0.5,en;q=0.3",
	}

class LZString:
	def __init__(self):
		self.vm = None

	def init(self, html, url):
		if self.vm:
			return
		cryptojs = re.search(r'src="([^"]+?/crypt_\w+?\.js)"', html).group(1)
		cryptojs = grabhtml(urljoin(url, cryptojs), referer=url)
		self.vm = VM(f"window = self; {cryptojs}; delete String.prototype.splic;")
		self.vm.create()

	def decompress_from_base64(self, data):
		return self.vm.call("LZString.decompressFromBase64", data)

lzstring = LZString()

def get_title(html, url):
	return re.search(r'<h1>([^<]*)', html).group(1)

def get_list(html, cid):
	ep_re = r'href="(/comic/{}/\d+\.html)" title="([^"]+)"|<h4><span>([^<]+)'.format(cid)
	arr = []
	try:
		comment_pos = html.index('id="Comment"')
	except ValueError:
		comment_pos = len(html)

	prefix = ""
	for match in re.finditer(ep_re, html):
		if match.start() >= comment_pos:
			break
		ep_url, title, new_prefix = match.groups()
		if new_prefix:
			prefix = new_prefix
			continue
		arr.append(("{} {}".format(prefix, title), ep_url))
	return arr


def get_episodes(html, url):
	lzstring.init(html, url)

	episodes = None
	cid = re.search(r"comic/(\d+)", url).group(1)
	
	# http://tw.ikanman.com/comic/10924/
	episodes = get_list(html, cid)
	
	# http://tw.ikanman.com/comic/4350/
	if not episodes:
		view_state = re.search(
			r'id="__VIEWSTATE" value="([^"]+)', html).group(1)
		ep_html = lzstring.decompress_from_base64(view_state)
		episodes = get_list(ep_html, cid)
		
	episodes = [Episode(v[0].strip(), urljoin(url, v[1])) for v in episodes]
	return episodes[::-1]
	
servers = None

def get_images(html, url):
	# build js context
	js = """
	var window = self;
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
		r'src="([^"]+?/config_\w+?\.js)"',
		html
	).group(1)
	configjs = grabhtml(urljoin(url, configjs_url), referer=url)
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
		files, path, params = vm.run("[cInfo.files, cInfo.path, cInfo.sl]")
	
	corejs_url = re.search(
		r'src="([^"]+?/core_\w+?\.js)"',
		html
	).group(1)
	corejs = grabhtml(urljoin(url, corejs_url), referer=url)
	
	# cache server list
	m = re.search(r"自动|自動", configjs)
	s = balance(configjs, m.start(), "[", "]")
	servs = eval(s)
	servs = [host["h"] for category in servs for host in category["hosts"]]
	
	global servers
	servers = cycle(servs)

	host = next(servers)
	
	utils = re.search(r"SMH\.(utils=[\s\S]+?);SMH\.imgData=", corejs).group(1)
	
	js = """
	const location = {
		protocol: "https:"
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
		
	params = urlencode(params)
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
