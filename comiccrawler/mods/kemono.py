"""
https://kemono.party/{service}/user/{id}
"""

import json
import re

from comiccrawler.error import SkipPageError
from comiccrawler.url import update_qs

from ..core import Episode
from ..grabber import grabber

domain = ["kemono.party", "kemono.su", "coomer.su"]
name = "Kemono"
noepfolder = True
next_page_cache = {}

def get_title(html, url):
	sig = re.search(r"\w+/user/\d+", url).group()
	data = grabber(f"https://kemono.su/api/v1/{sig}/profile").json()
	service = data["service"]
	name = data["name"]
	return f"[Kemono][{service}] {name}"

def get_episodes(html, url):
	if "/api/v1/" not in url:
		sig = re.search(r"\w+/user/\d+", url).group()
		next_page_cache[url] = f"https://kemono.su/api/v1/{sig}/posts-legacy"
		raise SkipPageError

	data = json.loads(html)
	episodes = []
	for result, attachments in zip(data["results"], data["result_attachments"]):
		if not attachments:
			continue
		ep = Episode(
			title=f"{result['id']} - {result['title']}",
			url=f"https://kemono.su/post/{result['id']}",
			image=[f"{a['server']}/data{a['path']}" for a in attachments]
			)
		episodes.append(ep)

	try:
		def next_o(o):
			new_o = int(o or "0") + data["props"]["limit"]
			if new_o >= data["props"]["count"]:
				raise StopIteration
			return str(new_o)
		next_page_cache[url] = update_qs(url, {"o": next_o})
	except StopIteration:
		pass

	episodes.reverse()
	return episodes

# def get_images(html, url):
# 	result = []
# 	for match in re.finditer(r'<a[^>]*href="([^"]*)"\s+download', html):
# 		result.append(match.group(1))
# 	if not result:
# 		raise SkipEpisodeError(True)
# 	return result

def get_next_page(html, url):
	# if "/post/" in url:
	# 	return None
	# match = re.search(r'<a href="([^"]+)"[^>]*class="next"', html)
	# if match:
	# 	return urljoin(url, match.group(1))
	return next_page_cache.pop(url, None)
