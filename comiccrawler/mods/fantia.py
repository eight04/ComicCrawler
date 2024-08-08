#! python3
import re
from html import unescape
from urllib.parse import urlparse

from ..episode import Episode
from ..grabber import grabber, grabhtml
from ..url import urljoin
from ..session_manager import session_manager
from ..util import clean_tags

domain = ["fantia.jp"]
name = "fantia"
config = {
	"curl": "",
	"api_curl": ""
}
noepfolder = True
autocurl = True

def session_key(url):
	r = urlparse(url)
	if r.path.startswith("/api"):
		return (r.scheme, r.netloc, "/api")

def get_title(html, url):
	name = re.search('<h1 class="fanclub-name">(.+?)</h1', html).group(1)
	return f"[fantia] {clean_tags(name)}"
	
def get_episodes(html, url):
	result = []
	for match in re.finditer(r'<a[^>]+href="(/posts/(\d+))"[^>]+title="([^"]+)', html):
		ep_url, ep_id, ep_title = match.groups()
		title = f"{ep_id} - {unescape(ep_title)}"
		result.append(Episode(url=urljoin(url, ep_url), title=title))
	return result[::-1]

def init_api_session(html):
	session = session_manager.get("https://fantia.jp/api/v1/posts/")
	if "X-CSRF-Token" in session.headers:
		return
	csrf_token = re.search('csrf-token" content="([^"]+)', html).group(1)
	session.headers.update({
		"X-CSRF-Token": csrf_token,
		"X-Requested-With": "XMLHttpRequest",
		})

def get_images(html, url):
	post_id = re.search(r"posts/(\d+)", url).group(1)
	init_api_session(html)
	result = grabber(f"https://fantia.jp/api/v1/posts/{post_id}", referer=url).json()
	try:
		thumb = result["post"]["thumb"]["original"]
	except (TypeError, KeyError): # thumb may be None
		thumb = None
	if thumb:
		yield thumb
	for content in result["post"]["post_contents"]:
		for photo in content.get("post_content_photos", []):
			i_html = grabhtml(urljoin(url, photo["show_original_uri"]), referer=url)
			yield unescape(re.search('<img src="([^"]+)', i_html).group(1))
		if "download_uri" in content:
			yield urljoin(url, content["download_uri"])
				
def get_next_page(html, url):
	match = re.search('<a rel="next"[^>]*href="([^"]+)', html)
	if match:
		return urljoin(url, match.group(1))
