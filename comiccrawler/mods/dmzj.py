#! python3
"""
http://manhua.dmzj.com/fklmfsnyly/

"""

import re
import json
from urllib.parse import urljoin

from deno_vm import eval

from ..core import Episode, grabhtml

domain = ["manhua.dmzj.com"]
name = "動漫之家"

def get_title(html, url):
	return re.search("<h1>(.+?)</h1>", html).group(1)

def get_episodes(html, url):
	result = None
	for method in (get_episodes_html, get_episodes_ajax):
		result = method(html, url)
		if result:
			break
	return result
	
def get_episodes_html(html, url):
	comicurl = re.search("comic_url = \"(.+?)\"", html).group(1)
	pattern = (
		r'href="(/{}[^"]+)" (?: class="color_red")?>(.+?)</a>\s*</li>'
			.format(comicurl)
	)
	s = []
	for match in re.finditer(pattern, html):
		ep_url, title = match.groups()
		s.append(Episode(title, urljoin(url, ep_url)))
	return s
	
def get_episodes_ajax(html, url):
	# http://manhua.dmzj.com/lzsyuan/
	comic_id = re.search('g_comic_id = "([^"]+)', html).group(1)
	data = grabhtml(f'http://api.dmzj.com/dynamic/comicinfo/{comic_id}.json')
	data = json.loads(data)
	s = []
	for chapter in data["data"]["list"]:
		title = chapter["chapter_name"]
		ep_url = urljoin(url, f"{chapter['id']}.shtml?cid={comic_id}")
		s.append(Episode(title, ep_url))
	return reversed(s)
	
def get_images(html, url):
	try:
		return get_images_eval(html, url)
	except AttributeError:
		pass
	return get_images_ajax(html, url)
	
def get_images_ajax(html, url):
	chapter_id, comic_id = re.search(r"(\d+)\.shtml\?cid=(\d+)", url).groups()
	data = grabhtml(f"https://m.dmzj.com/chapinfo/{comic_id}/{chapter_id}.html")
	data = json.loads(data)
	return data["page_url"]

def get_images_eval(html, url):
	# Set base url
	base = "http://images.dmzj.com/"

	# Get urls
	html = html.replace("\n", "")
	s = re.search(r"page = '';\s*(.+?);\s*var g_comic_name", html).group(1)
	pages = eval(s + "; pages")
	pages = eval(pages)

	# thumbs.db?!
	# http://manhua.dmzj.com/zhuoyandexiana/3488-20.shtml
	return [base + page for page in pages if page and not page.lower().endswith("thumbs.db")]
