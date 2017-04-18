#! python3

import json
import re

from ..core import Episode, grabhtml
from ..url import urljoin

domain = ["smp.yoedge.com"]
name = "yoedge"

def get_title(html, url):
	return re.search(r"<title>([^<]+)", html).group(1)

def get_episodes(html, url):
	html = html[:html.index("am-topbar-fixed-bottom")]
	s = []
	
	for m in re.finditer(r'<a [^>]*?href="([^"]*?/smp-app/[^"]*)">([^<]+)', html):
		ep_url, title = m.groups()
		s.append(Episode(title, ep_url))
	return s

def get_images(html, url):
	cfg = grabhtml(urljoin(url, "smp_cfg.json"))
	cfg = json.loads(cfg)
	
	pages = [cfg["pages"]["page"][i] for i in cfg["pages"]["order"]]
	return [urljoin(url, p) for p in pages]
