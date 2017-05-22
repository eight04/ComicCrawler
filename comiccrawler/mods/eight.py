#! python3

"""this is 8comic module for comiccrawler.

"""

import re
from urllib.parse import urljoin

from node_vm2 import VM

from ..core import Episode, grabhtml, clean_tags

domain = ["www.8comic.com", "www.comicvip.com", "www.comicbus.com"]
name = "無限"

def get_title(html, url):
	return re.search("<font color=\"#FF6600\" style=\"font:12pt;"
			"font-weight:bold;\">(.+?)</font>",html).group(1)

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
	m = re.search("ch=(\d+)", url)
	if m is None:
		ch = "1"
	else:
		ch = m.group(1)

	def ss(str): # pylint: disable=invalid-name
		return re.sub("[a-z]+", "", str)

	cs = re.search("cs='([^']+)", html).group(1)
	ti = re.search("ti=(\d+);", html).group(1)

	i = 0
	while i < len(cs):
		if ch == ss(cs[i:i+4]):
			code = cs[i:i+50]
			break
		i += 50
	else:
		code = cs[-50:]

	pages = int(ss(code[7:10]))

	s = []
	for p in range(1, pages + 1):
		hash = (((p - 1) // 10) % 10) + (((p - 1) % 10) * 3)
		src = "http://img{}.8comic.com/{}/{}/{}/{:03}_{}.jpg".format(
				ss(code[4:6]), code[6:7], ti, ch, p, code[hash + 10:hash + 13])
		s.append(src)
	return s
