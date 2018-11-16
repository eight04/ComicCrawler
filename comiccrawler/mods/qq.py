#! python3

"""
http://ac.qq.com/Comic/comicInfo/id/626619
"""

import re
import node_vm2

from ..core import Episode
from ..grabber import grabhtml
from ..url import urljoin

domain = ["ac.qq.com"]
name = "騰訊"

def get_title(html, url):
	return re.search(r'<h2 class="works-intro-title[^>]+><strong>([^<]+)', html).group(1)

def get_episodes(html, url):
	rx = "class='works-chapter-item'.+?<a[^>]+?title=\"([^\"]+)[^>]+?href=\"([^\"]+)"
	end_index = html.index('class="chapter-page-new')
	episodes = []
	for match in re.finditer(rx, html, re.DOTALL):
		if match.start() >= end_index:
			break
		title, ep_url = match.groups()
		ep_id = re.search("\d+$", ep_url).group()
		title = "{ep_id} - {title}".format(ep_id=ep_id, title=title)
		ep_url = urljoin(url, ep_url)
		episodes.append(Episode(title, ep_url))
	return episodes
	
def get_images(html, url):
	data = re.search("var DATA\s*=\s*'[^']+'", html).group()
	nonce = re.search("window\.nonce = (.+)", html).group(1)
	nonce2 = re.search("window\[.+?=(.+)", html)
	nonce2 = nonce2.group(1) if nonce2 else None
	
	view_js = re.search('src="([^"]+?page\.chapter\.view[^"]+?\.js[^"]+)', html).group(1)
	view_js = grabhtml(urljoin(url, view_js))
	view_js = re.search("(eval\(.+?)\}\(\)", view_js, re.DOTALL).group(1)
	
	code = data + ";var nonce = " + (nonce2 or nonce) + ";var W = {DATA, nonce};" + view_js + ";_v"
	
	data = node_vm2.eval(code)
	return [p["url"] for p in data["picture"]]
