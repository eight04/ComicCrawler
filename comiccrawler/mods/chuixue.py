#! python3

"""吹雪動漫"""

import re, base64
from ..core import Episode
from urllib.parse import urljoin

domain = ["www.chuixue.com"]
name = "吹雪"

def gettitle(html, url):
	return re.search("wdname='([^']+)'", html).group(1)

def getepisodelist(html, url, last_episode):
	id = re.search("manhua/(\d+)", url).group(1)
	s = []
	for match in re.finditer('<a href="(/manhua/' + id + '/\d+\.html)"[^>]*>([^<]+)', html):
		ep_url, title = match.groups()
		s.append(Episode(title, urljoin(url, ep_url)))
	return s[::-1]

def decode(s):
	return base64.b64decode(s).decode("utf8")

def encode(s):
	return base64.b64encode(s).decode("utf8")

def getimgurls(html, url):
	qTcms_S_m_murl_e = re.search('qTcms_S_m_murl_e="([^"]+)"', html).group(1)

	imgs = decode(qTcms_S_m_murl_e).split("$qingtiandy$")

	web_dir = re.search('web_dir="([^"]*)"', html).group(1)

	def realpic(url):
		if "manhuaju.com" in url or "bengou.com" in url:
			return web_dir + "qTcms_Inc/qTcms.Pic.FangDao.asp?p=" + encode(url);
		return url

	return [realpic(img) for img in imgs]
