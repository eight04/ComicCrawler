#! python3

"""this is 99comic module for comiccrawler

Ex:
	http://www.99comic.com/comic/9910481/
	
"""

import re
from urllib.parse import urljoin
from ..core import Episode

domain = ["www.99comic.com"]
name = "99"

def get_title(html, url):
	return re.search("<h1><a title='([^']+)'", html).group(1)
	
def get_episodes(html, url):
	s = []
	base = re.search("(https?://[^/]+)", url).group(1)
	for m in re.finditer("href='(/comics/[^']+/)'>([^<]+)</a>(?!</li>)", html):
		ep_url, title = m.groups()
		s.append(Episode(title, urljoin(url, ep_url)))
	return s[::-1]

def get_images(html, url):	
	ds = [
		"http://218.24.35.163:9393/dm01/",
		"http://218.24.35.163:9393/dm02/",
		"http://218.24.35.163:9393/dm03/",
		"http://218.24.35.163:9393/dm04/",
		"http://218.24.35.163:9393/dm05/",
		"http://218.24.35.163:9393/dm06/",
		"http://218.24.35.163:9393/dm07/",
		"http://218.24.35.163:9393/dm08/",
		"http://218.24.35.163:9393/dm09/",
		"http://218.24.35.163:9393/dm10/",
		"http://112.123.174.23:9292/dm11/",
		"http://218.24.35.163:9393/dm12/",
		"http://218.24.35.163:9393/dm13/",
		"http://173.231.57.238/dm14/",
		"http://218.24.35.163:9393/dm15/",
		"http://142.4.34.102/dm16/"
	]
	
	sfiles = re.search("sFiles=\"([^\"]+)\"", html).group(1)
	spath = re.search("sPath=\"(\d+)\"", html).group(1)
	
	imgs = sfiles.split("|")
	base = ds[int(spath) - 1]
	
	return [base + i for i in imgs]
