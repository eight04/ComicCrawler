#! python3
"""
http://manhua.dmzj.com/fklmfsnyly/

"""

import re
import json
from urllib.parse import urljoin

from node_vm2 import eval

from ..core import Episode, grabhtml

domain = ["manhua.dmzj.com"]
name = "動漫之家"

def get_title(html, url):
	return re.search("<h1>(.+?)</h1>", html).group(1)

def get_episodes(html, url):
	comicurl = re.search("comic_url = \"(.+?)\"", html).group(1)
	pattern = (
		r'href="(/{}[^"]+)" (?: class="color_red")?>(.+?)</a>\s*</li>'
			.format(comicurl)
	)
	s = []
	for match in re.finditer(pattern, html):
		ep_url, title = match.groups()
		s.append(Episode(title, urljoin(url, ep_url)))
		
	if not s:
		s = get_episodes_ajax(html, url)
		
	return s
	
def get_episodes_ajax(html, url):
	# http://manhua.dmzj.com/lzsyuan/
	comic_id = re.search('g_comic_id = "([^"]+)', html).group(1)
	data = grabhtml('http://v2.api.dmzj.com/comic/{comic_id}.json?channel=Android&version=2.6.004'.format(comic_id=comic_id))
	data = json.loads(data)
	s = []
	for i, chapter in enumerate(data["chapters"]):
		for ep in chapter["data"]:
			title = ep["chapter_title"]
			ep_url = urljoin(url, "{ep[chapter_id]}.shtml?cid={comic_id}".format(ep=ep, comic_id=comic_id))
			if i == 0 and re.match("\d", title):
				title = "第" + title
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
	data = grabhtml("http://v2.api.dmzj.com/chapter/{comic_id}/{chapter_id}.json?channel=Android&version=2.6.004".format(comic_id=comic_id, chapter_id=chapter_id))
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
