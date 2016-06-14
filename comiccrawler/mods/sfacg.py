#! python3

"""this is sfacg module for comiccrawler

Ex:
	http://comic.sfacg.com/HTML/PFSLL/

"""

import re

from ..core import Episode, grabhtml

domain = ["comic.sfacg.com"]
name = "SF"

def get_title(html, url):
	html = html.replace("\n","")
	t = re.search("<title>(.+?)</title>", html).group(1)
	return t.split(",")[0]

def get_episodes(html, url):
	base = re.search("(https?://[^/]+)", url).group(1)
	s = []
	for m in re.findall("<li><a href=\"(.+?)\" target=\"_blank\">(.+?)</a></li>", html, re.M):
		url, title = m
		title = re.sub("<.+?>","",title)
		e = Episode(title, base + url)
		s.append(e)
	return s[::-1]

def get_images(html, url):
	js = re.search("src=\"(/Utility/.+?\.js)\"", html).group(1)
	base = re.search("(https?://[^/]+)", url).group(1)

	htmljs = grabhtml(base + js)
	# host = "http://coldpic.sfacg.com"
	pics = re.findall("picAy\[\d+\] = \"(.+?)\"", htmljs)
	return [base + pic for pic in pics]
