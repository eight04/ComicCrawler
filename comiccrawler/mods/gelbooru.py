#! python3

"""this is gelbooru module for comiccrawler

Example:
	https://gelbooru.com/index.php?page=post&s=list&tags=hiroyama_hiroshi
	https://gelbooru.com/index.php?page=pool&s=show&id=45250
	https://gelbooru.com/index.php?page=post&s=list&tags=nakajima_ryou

"""

from html import unescape
import re

from ..url import urljoin
from ..core import Episode

domain = ["gelbooru.com"]
name = "Gelbooru"
noepfolder = True

cookie = {
	"fringeBenefits": "yup"
}

def is_pool(url):
	return "page=pool" in url

def get_title(html, url):
	if is_pool(url):
		title = unescape(re.search("<h3>Now Viewing: ([^<]+)", html).group(1))
		pool_id = re.search("id=(\d+)", url).group(1)
		return "[Gelbooru] {title} ({pool_id})".format(title=title, pool_id=pool_id)
	title = unescape(re.search("<title>([^<]+?)\|\s+(?:Gelbooru|Page)", html).group(1).strip())
	return "[Gelbooru] {title}".format(title=title)

def get_episodes(html, url):
	s = []
	for match in re.finditer(r'<a[^>]+?href="((?:(?:https:)?//gelbooru\.com/)?index\.php\?page=post&(?:amp;)?s=view[^"]+)', html):
		ep_url = unescape(match.group(1))
		id = re.search(r"\bid=(\d+)", ep_url).group(1)
		s.append(Episode(id, urljoin(url, ep_url)))
	if is_pool(url):
		return s
	return s[::-1]
	
def get_next_page(html, url):
	paginator_index = html.find('<div id="paginator">')
	if paginator_index >= 0:
		rx = re.compile(r'</b>\s*<a href="([^"]+)')
		match = rx.search(html, paginator_index)
		if match:
			return urljoin(url, unescape(match.group(1)))

def get_images(html, url):
	img = re.search('<a href="([^"]+)"[^>]*>Original image', html).group(1)
	return img
	