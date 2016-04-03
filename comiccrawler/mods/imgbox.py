#! python3

import re
from html import unescape
from urllib.parse import urljoin

from ..core import Episode, grabhtml
from ..safeprint import safeprint

domain = ["imgbox.com"]
name = "imgbox"
noepfolder = True

def gettitle(html, url):
	title = re.search(r'<h1>([^<]+)</h1>', html).group(1)
	title = re.sub(r" - \d+ images$", "", title)
	return "[imgbox] " + title

def getepisodelist(html, url, last_episode):
	s = []
	for match in re.finditer(r'href="(/(\w+))"><img', html):
		ep_url, id = match.groups()
		s.append(Episode(id, urljoin(url, ep_url)))
	return s

def getimgurls(html, url):
	img = re.search(r'href="([^?"]+\?download=true)"', html).group(1)
	return [img]
