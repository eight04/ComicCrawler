#! python3

"""this is buka module for comiccrawler

Ex:
	http://www.buka.cn/detail/202796

"""

import re

from urllib.parse import urljoin

from ..core import Episode

domain = ["www.buka.cn"]
name = "布卡"

def get_title(html, url):
	return re.search(r'class="title-font">([^<]*)', html).group(1).strip()

def get_episodes(html, url):
	rx = '<a[^>]+href="(/view/[^"]+)"[^>]*>([^<]+)'
	arr = []
	for match in re.finditer(rx, html):
		ep_url, title = match.groups()
		title = title.strip()
		arr.append(Episode(title, urljoin(url, ep_url)))
	return arr[::-1]
	
def get_images(html, url):
	return re.findall('="([^"]+?/pics/[^"]+?)"', html)
