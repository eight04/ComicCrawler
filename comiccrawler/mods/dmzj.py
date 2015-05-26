#! python3
"""
http://manhua.dmzj.com/fklmfsnyly/

"""

import re, execjs

from ..core import Episode

domain = ["manhua.dmzj.com"]
name = "動漫之家"

def gettitle(html, url):
	return re.search("<h1>(.+?)</h1>", html).group(1)
	
def getepisodelist(html, url):
	base = re.search("(https?://[^/]+)", url).group(1)
	comicurl = re.search("comic_url = \"(.+?)\"", html).group(1)
	ms = re.findall("href=\"(/{}.+?)\" (?: class=\"color_red\")?>(.+?)</a></li>".format(comicurl), html)
	s = []
	for m in ms:	
		url, title = m
		e = Episode(title, base + url)
		s.append(e)
	return s

def getimgurls(html, url):
	# Set base url
	base = "http://images.dmzj.com/"
	
	# Get urls
	html = html.replace("\n", "")
	s = re.search("page = '';(.+?);var g_comic_name", html).group(1)
	pages = execjs.compile(s).eval("pages");
	pages = execjs.eval(pages);
	
	# thumbs.db?!
	# http://manhua.dmzj.com/zhuoyandexiana/3488-20.shtml
	return [base + page for page in pages if page and not page.lower().endswith("thumbs.db")]
	