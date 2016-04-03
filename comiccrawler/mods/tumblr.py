#! python3

"""this is konachan module for tumblr

Ex:
	http://otn-pct.tumblr.com/

"""

import re, json
from urllib.parse import urljoin

from ..core import Episode, grabhtml
from ..safeprint import safeprint

domain = ["tumblr.com"]
name = "tumblr"
noepfolder = True

def get_title(html, url):
	title = re.search(r"<title>([^<]+)", html).group(1)
	id = url[url.index("://") + 3: url.index(".tumblr.com")]
	return "[tumblr] {} ({})".format(title, id)
	
def get_episodes(html, url):
	s = []
	# base = re.search("(https?://[^/]+)", url).group(1)
	pattern = 'href="(' + re.escape(urljoin(url, "/post/")) + '(\d+))'
	for m in re.finditer(pattern, html):
		url, uid = m.groups()
		s.append(Episode(uid, url))
	return s[::-1]
			
def get_images(html, url):
	s = re.search('<script type="application/ld\+json">([^<]*)</script>', html).group(1)
	o = json.loads(s)
	if isinstance(o["image"], str):
		return [o["image"]]
	return o["image"]["@list"]

def get_next_page(html, url):
	match = re.search('<a href="([^"]+)" id="next">', html)
	if match:
		return urljoin(url, match.group(1))
