#! python3

import re
from urllib.parse import urljoin
from ..core import Episode, grabhtml

domain = ["www.99comic.com", "99.hhxxee.com"]
name = "99"

def get_title(html, url):
	return re.search("<h1><a title='([^']+)'", html).group(1)
	
def get_episodes(html, url):
	s = []
	# base = re.search("(https?://[^/]+)", url).group(1)
	for m in re.finditer("href='(/comics/[^']+/)'>([^<]+)</a>(?!</li>)", html):
		ep_url, title = m.groups()
		s.append(Episode(title, urljoin(url, ep_url)))
	return s[::-1]

def get_images(html, url):
	viewhtml_js = re.search('src="([^"]+viewhtml\.js)"', html).group(1)
	viewhtml_js = grabhtml(urljoin(url, viewhtml_js))
	
	ds = re.search('sDS = "([^"]+)', viewhtml_js).group(1)
	ds = ds.split("|")
	
	sfiles = re.search("sFiles=\"([^\"]+)\"", html).group(1)
	spath = re.search("sPath=\"(\d+)\"", html).group(1)
	
	imgs = sfiles.split("|")
	base = ds[int(spath) - 1]
	
	return [base + i for i in imgs]
