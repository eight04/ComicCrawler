#! python3

import re
from html import unescape

from ..core import Episode
from ..url import urljoin
from ..util import clean_tags

domain = ["nijie.info"]
name = "nijie"
noepfolder = True
config = {
	"cookie_n_session_hash": "",
	"cookie_nemail": "",
	"cookie_nlogin": ""
}

def get_title(html, url):
	match = re.search(
		r'<a class="name" href="members\.php\?id=(\d+)">(.+?)</a>', html)
	uid, name = match.groups()
	
	name = clean_tags(name)
	
	if "dojin.php" in url:
		name += " (dojin)"
		
	return "[nijie] {id} - {name}".format(id=uid, name=name)

def get_episodes(html, url):
	s = []
	ep_set = set()
	
	for m in re.finditer(r'<a href="(/view\.php\?id=(\d+))" title="([^"]+)', html):
		ep_url, ep_id, title = m.groups()
		if ep_id in ep_set:
			continue
		ep_set.add(ep_id)
		
		title = "{} - {}".format(ep_id, unescape(title))
		ep_url = urljoin(url, ep_url)
		
		s.append(Episode(title, ep_url))
		
	return s[::-1]
	
def clean_rs(url):
	return re.sub("/__rs_[^/]+", "", url)
	
def get_images(html, url):
	try:
		html = html[html.index('id="view-center"'):]	
	except ValueError:
		pass
	html = html[:html.index('id="nuitahito')]
	
	matches = re.finditer(r'<img[^>]+src="([^"]+)[^>]+data-original', html)
	matches = list(matches)
	if not matches:
		matches = re.finditer(r'<img[^>]+?illust_id=[^>]+?src="([^"]+)', html)
	return list(urljoin(url, clean_rs(m.group(1))) for m in matches)

def get_next_page(html, url):
	match = re.search(r'<a rel="next" href="([^"]+)', html)
	if match:
		return urljoin(url, match.group(1))
