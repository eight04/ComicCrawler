#! python3

"""this is seemh module for comiccrawler

Ex:
	http://tw.seemh.com/comic/10924/
	http://www.seemh.com/comic/10924/

"""

import re, execjs

from urllib.parse import urljoin

from ..core import Episode, grabhtml

domain = ["tw.seemh.com", "www.seemh.com"]
name = "看漫畫"

def gettitle(html, url):
	return re.search(r'<h1>([^<]*)', html).group(1)

def getepisodelist(html, url):
	cid = re.search(r"comic/(\d+)", url).group(1)
	ep_re = r'href="(/comic/{}/\d+\.html)" title="([^"]+)"'.format(cid)
	arr = []
	comment_pos = html.index('class="comment-bar"')
	for match in re.finditer(ep_re, html):
		if match.start() >= comment_pos:
			break
		ep_url, title = match.groups()
		arr.append(Episode(title, urljoin(url, ep_url)))
	return arr[::-1]

def getimgurls(html, url):
	configjs_url = re.search(
		r"http://statictw\.seemh\.com/scripts/config_\w+?\.js",
		html
	).group()
	configjs = grabhtml(configjs_url, referer=url)
	crypto = re.search(r"(var CryptoJS.+?)var pVars", configjs, re.S).group(1)

	info_eval = re.search(
		r'<script type="text/javascript">(eval[^<]+)',
		html
	).group(1)

	ctx = execjs.compile(crypto + info_eval)
	files, path = ctx.eval("[cInfo.files, cInfo.path]")

	return ["http://i.seemh.com:88" + path + file for file in files]
