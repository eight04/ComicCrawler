#! python3
import re
from html import unescape

from ..episode import Episode
from ..grabber import grabber, grabhtml
from ..url import urljoin
from ..util import clean_tags

domain = ["fantia.jp"]
name = "fantia"
config = {
	"curl": ""
}
noepfolder = True
autocurl = True

next_page_cache = {}
pin_entry_cache = {}

def get_title(html, url):
	name = re.search('<h1 class="fanclub-name">(.+?)</h1', html).group(1)
	return f"[fantia] {clean_tags(name)}"
	
def get_episodes(html, url):
	result = []
	for match in re.finditer('<a[^>]+href="(/posts/(\d+))"[^>]+title="([^"]+)', html):
		ep_url, ep_id, ep_title = match.groups()
		title = f"{ep_id} - {unescape(ep_title)}"
		result.append(Episode(url=urljoin(url, ep_url), title=title))
	return result[::-1]

def get_images(html, url):
	post_id = re.search("posts/(\d+)", url).group(1)
	result = grabber(f"https://fantia.jp/api/v1/posts/{post_id}").json()
	thumb = result["post"].get("thumb", {}).get("original")
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
