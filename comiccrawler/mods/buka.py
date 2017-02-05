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
	arr = []
	for match in re.finditer(r"payChapter\('(.+?)','(.+?)'[^>]+>([^<]+)", html):
		ep_url, title, chapter = match.groups()
		chapter = chapter.strip()
		arr.append(Episode("{chapter} ({title})".format(chapter=chapter, title=title), urljoin(url, ep_url)))
	return arr[::-1]
	
def get_images(html, url):
	return re.findall('="([^"]+?/pics/[^"]+?)"', html)
