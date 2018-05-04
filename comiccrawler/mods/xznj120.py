#! python3

"""this is xznj120 module for comiccrawler

Example:
	http://www.xznj120.com/lianai/591/

"""

from base64 import b64decode
from html import unescape
import re

from ..url import urljoin
from ..core import Episode

domain = ["www.xznj120.com"]
name = "受漫畫"

def get_title(html, url):
	return re.search("<h1>([^<]+)", html).group(1)

def get_episodes(html, url):
	s = []
	for match in re.finditer(r'<li><a href="([^"]+)"[^>]+><p>([^<]+)', html):
		ep_url, title = [unescape(t) for t in match.groups()]
		s.append(Episode(title, urljoin(url, ep_url)))
	return s[::-1]
	
def get_images(html, url):
	data = re.search('qTcms_S_m_murl_e="([^"]+)', html).group(1)
	imgs = b64decode(data).decode("latin-1").split("$qingtiandy$")
	return [urljoin(url, i) for i in imgs]
	