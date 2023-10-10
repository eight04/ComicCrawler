#! python3

"""
https://163.bilibili.com/source/5302242712730021771
"""

import json
import re
from html import unescape
from deno_vm import eval

from ..core import Episode
from ..grabber import grabhtml

domain = ["163.bilibili.com"]
name = "bilibili"

def get_title(html, url):
	title = re.search(r'<h1 class="f-toe sr-detail__heading">([^<]+)', html).group(1)
	return unescape(title.strip())

def get_episodes(html, url):
	id = re.search("source/(\d+)", url).group(1)
	info_url = "https://163.bilibili.com/book/catalog/{}.json".format(id)
	data = json.loads(grabhtml(info_url))
	s = [Episode(
		section["fullTitle"],
		"https://163.bilibili.com/reader/{}/{}".format(id, section["sectionId"])
	) for section in data["catalog"]["sections"][0]["sections"]]
	return s

def get_images(html, url):
	js = re.search(r"(window\.DATA = [\s\S]+?)</script>", html).group(1)
	imgs = eval("""
	const window = {};
	""" + js + """
	window.PG_CONFIG.images.map(i => i.url.slice(0, i.url.length - window.DATA.seedLength));
	""")
	return imgs
