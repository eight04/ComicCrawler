#! python3

"""iibq

Ex:
	http://www.aacomic.com/manhua/blgl20978/

"""

from itertools import cycle
import re

from deno_vm import VM

from ..core import Episode, grabhtml
from ..url import urlparse, urlupdate, urljoin
from ..error import is_http

domain = ["www.aacomic.com"]
name = "暗暗"

def get_title(html, url):
	title = re.search(r"<h1><a.+?>([^<]+)", html, re.DOTALL).group(1)
	return title.strip()
	
def get_episodes(html, url):
	s = []
	html = html[html.index('<div class="cVol'):]
	pattern = r"href='(http://www\.aacomic\.com/comics/\d+viewpage\d+/)'>([^<]+)"
	for match in re.finditer(pattern, html):
		u, title = match.groups()
		s.append(Episode(title, u))
			
	return s[::-1]
	
servers = None

def get_images(html, url):
	s_files = re.search('sFiles="([^"]+)', html).group(1)
	s_path = re.search('sPath="([^"]+)', html).group(1)
	
	viewhtm = re.search(r'src="([^"]*?viewhtm\d*\.js[^"]*)', html)
	viewhtm = grabhtml(urljoin(url, viewhtm.group(1)))
	
	env = """
	window = {
		"eval": eval,
		"parseInt": parseInt,
		"String": String,
		"RegExp": RegExp
	};
	const location = {
		"hostname": null
	};
	function setHostname(hostname) {
		location.hostname = hostname;
	}
	"""
	
	js = env + re.search(r'function isMobile\(\){.+?}(.+?)var cMod', viewhtm,
		re.DOTALL).group(1)
	with VM(js) as vm:
		vm.call("setHostname", urlparse(url).hostname)
		arr_files = vm.call("unsuan", s_files).split("|")
	
	ds = re.search(r"src='([^']*?ds\.js[^']*)", html)
	ds = grabhtml(urljoin(url, ds.group(1)))
	
	global servers
	servers = re.search('sDS = "([^"]+)', ds).group(1).split("^")
	servers = [s.split("|")[1] for s in servers]
	servers = cycle(servers)
	server = next(servers)
	return (server + s_path + f for f in arr_files)
	
def errorhandler(err, crawler):
	if not is_http(err):
		return
		
	if not crawler.image or not crawler.image.url:
		return
		
	server = next(servers)
	crawler.image = urlupdate(crawler.image, netloc=server)
