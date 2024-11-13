"""
https://kemono.party/{service}/user/{id}
"""

import re
from urllib.parse import urljoin

from comiccrawler.error import SkipEpisodeError

from ..core import Episode

domain = ["kemono.party", "kemono.su", "coomer.su"]
name = "Kemono"
noepfolder = True

def get_title(html, url):
	service = re.search('<meta name="service" content="([^"]+)', html).group(1) # type: ignore
	name = re.search('<meta name="artist_name" content="([^"]+)', html).group(1) # type: ignore
	return f"[Kemono][{service}] {name}"

def get_episodes(html, url):
	result = []
	for match in re.finditer(r'<a href="([^"]+/post/(\d+))">\s*<header[^>]*>([^<]*)</header>', html):
		id = match.group(2).strip()
		title = match.group(3).strip()
		result.append(Episode(
			title=f"{id} - {title}",
			url=urljoin(url, match.group(1))
		))
	result.reverse()
	return result

def get_images(html, url):
	result = []
	for match in re.finditer(r'<a[^>]*href="([^"]*)"\s+download', html):
		result.append(match.group(1))
	if not result:
		raise SkipEpisodeError(True)
	return result

def get_next_page(html, url):
	if "/post/" in url:
		return None
	match = re.search(r'<a href="([^"]+)"[^>]*class="next"', html)
	if match:
		return urljoin(url, match.group(1))
