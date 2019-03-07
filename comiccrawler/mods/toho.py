"""
https://www.tohomh.com/wuquan/
"""

import json
import re
from urllib.parse import urljoin

from ..core import Episode, grabhtml

domain = ["www.tohomh.com", "www.tohomh123.com"]
name = "土豪"

def get_title(html, url):
	return re.search('<h1>([^<]+)', html).group(1)

def get_episodes(html, url):
	base = re.match("https?://[^/]+/([^/]+)", url).group(1)
	pattern = '<a href="(/{}/[^"]+)[^>]+>([^<]+)'.format(base)
	try:
		start = html.index("detail-list-select-1")
	except ValueError:
		start = 0
	try:
		end = html.index("detail-list-select-2")
	except ValueError:
		end = len(html)
	s = []

	for match in re.finditer(pattern, html):
		if match.start() < start:
			continue
		if match.end() > end:
			break
		ep_url, title = match.groups()
		s.append(Episode(title, urljoin(url, ep_url)))
	return s[::-1]

def get_images(html, url):
	did = re.search("did=(\d+)", html).group(1)
	sid = re.search("sid=(\d+)", html).group(1)
	endpoint = urljoin(url, "/action/play/read")
	pcount = int(re.search("pcount = (\d+)", html).group(1))
	
	s = []
	for i in range(pcount):
		s.append(create_image_getter(endpoint, did, sid, i + 1))
	return s
		
def create_image_getter(url, did, sid, iid):
	def get():
		content = grabhtml(url, params={
			"did": did,
			"sid": sid,
			"iid": str(iid)
		})
		return json.loads(content)["Code"]
	return get
