#! python3

"""
http://ac.qq.com/Comic/comicInfo/id/626619
"""

import base64
import json
import re

from ..core import Episode
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
	data = re.search("var DATA\s*=\s*'.([^']+)", html).group(1)
	data = base64.b64decode(data).decode("latin-1")
	data = json.loads(data)
	return [p["url"] for p in data["picture"]]
