#! python3

"""this is weibo module for comiccrawler

Ex:
	http://tw.weibo.com/2362470852/4061673218817198

"""

import re

from ..core import Episode

domain = ["tw.weibo.com"]
name = "weibo"
noepfolder = True

def get_title(html, url):
	title = re.search('<title>([^<]+)', html).group(1)
	title = title.replace("- 微博精選 - 微博台灣站", "").replace("\n", "").strip()
	id = re.search('tw\.weibo\.com/([^/]+/\d+)', url).group(1)
	return "[weibo] {title} ({id})".format(title=title, id=id)

def get_episodes(html, url):
	return [Episode("image", url)]

def get_images(html, url):
	images = re.findall('<img src="([^"]+?sinaimg\.cn/bmiddle[^"]+)', html)
	return map(lambda i: i.replace("/bmiddle/", "/large/"), images)
