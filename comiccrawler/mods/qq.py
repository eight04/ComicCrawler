#! python3

"""
http://ac.qq.com/Comic/comicInfo/id/626619
"""

import re
from deno_vm import eval

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
	
def get_nonce(html):
	matches = list(re.finditer("window\[.+?=(.+)", html))
	if matches:
		return matches[-1].group(1)
	return re.search("window\.nonce = (.+)", html).group(1)
	
def get_images(html, url):
	data = re.search("var DATA\s*=\s*'[^']+'", html).group()
	nonce = get_nonce(html)
	
	view_js = re.search('src="([^"]+?page\.chapter\.view[^"]+?\.js[^"]*)', html).group(1)
	view_js = grabhtml(urljoin(url, view_js))
	view_js = re.search("(eval\(.+?)\}\(\)", view_js, re.DOTALL).group(1)
	
	code = "\n".join([
		data,
		"""
		function createDummy() {
			return new Proxy(() => true, {
				get: () => createDummy()
			});
		}
		const window = document = createDummy();
		""",
		"const nonce = {};".format(nonce),
		"const W = {DATA, nonce};",
		view_js
	])
	
	data = eval(code)
	return [p["url"] for p in data["picture"]]
