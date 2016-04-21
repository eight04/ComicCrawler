#! python3

"""this is manhuadao module for comiccrawler

Ex:
	(http://www.999comic.com/comic/3300/)
	http://www.manhuadao.com/book/wudaokuangzhishi/
	
"""

import re, execjs

from ..core import Episode, grabhtml

domain = ["www.manhuadao.com"]
name = "漫畫島"

def get_title(html, url):
	return re.search(r'class="book-title">\s*<h1>([^<]*)', html).group(1)
	
def get_episodes(html, url):
	s = []
	base, id = re.search(r"(https?://[^/]+)/book/([^/]+)", url).groups()
	
	for match in re.finditer(r'href="(/book/{}/[^"]+)" title="([^"]+)"'.format(id), html):
		url, title = match.groups()
		e = Episode(title, base + url)
		s.append(e)
		
	return s[::-1]

def get_images(html, url):
	base, protocol, id = re.search(r"((https?://)[^/]+)/book/([^/]+)", url).groups()
	
	core = re.search(r'src="(/scripts/core[^"]+)"', html).group(1)
	cInfo = re.search(r'cInfo = ({[^;]+});', html).group(1)
	
	coreJs = grabhtml(base + core, referer=url)
	pageConfig = re.search(r'pageConfig=({[^;]+})', coreJs).group(1)
	
	images = execjs.eval(cInfo)["fs"]
	host = execjs.eval(pageConfig)["host"]
	
	return [protocol + host + image for image in images]
