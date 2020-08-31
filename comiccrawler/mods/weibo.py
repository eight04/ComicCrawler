#! python3

"""this is weibo module for comiccrawler

Ex:
	http://tw.weibo.com/2362470852/4061673218817198
	http://tw.weibo.com/wulazula

"""

import re

from ..core import Episode
from ..url import urljoin
from ..error import SkipEpisodeError, is_http

domain = ["tw.weibo.com"]
name = "weibo"
noepfolder = True

def get_title(html, url):
	match = re.search("^http://tw\.weibo\.com/(\w+)$", url)
	if match:
		user_id = match.group(1)
		user_name = re.search('class="name">\s*<h3><a[^>]+>([^<]+)', html).group(1)
		return "[weibo] {user_id} - {user_name}".format(user_id=user_id, user_name=user_name)
	title = re.search('<title>([^<]+)', html).group(1)
	title = title.replace("- 微博精選 - 微博台灣站", "").replace("\n", "").strip()
	id = re.search('tw\.weibo\.com/([^?]+)', url).group(1)
	return "[weibo] {title} ({id})".format(title=title, id=id)

def get_episodes(html, url):
	if re.match("http://tw\.weibo\.com/\w+/\d+$", url):
		return [Episode("image", url)]
		
	s = []
	pattern = 'class="img_link" href="(http://tw.weibo.com/(\w+/\d+))">'
	for match in re.finditer(pattern, html):
		ep_url, ep_title = match.groups()
		s.append(Episode(ep_title, ep_url))
	return s[::-1]

def get_images(html, url):
	images = re.findall('<img src="([^"]+?sinaimg\.cn/bmiddle[^"]+)', html)
	return map(lambda i: i.replace("/bmiddle/", "/large/"), images)
	
def get_next_page(html, url):
	match = re.search('class="pgNext"><a href="([^"]+)"', html)
	if match:
		return urljoin(url, match.group(1))
		
def errorhandler(err, crawler):
	if is_http(err, 404) and re.search("weibo\.com/[^/]+/[^/]+$", err.request.url):
		raise SkipEpisodeError
