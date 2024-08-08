"""
https://{id}.fanbox.cc/posts
"""
import re
import json

from comiccrawler.error import SkipPageError

from ..episode import Episode
from ..error import SkipEpisodeError

domain = ["fanbox.cc"]
name = "fanbox"
config = {
	# "curl": "",
	"curl_api": ""
}
noepfolder = True
autocurl = True

next_page_cache = {}
# pin_entry_cache = {}

def get_title(html, url):
	name = re.search('<title>投稿一覽｜([^<]+)｜pixivFANBOX</title>', html).group(1)
	return f"[fanbox] {(name)}"
	
def get_episodes(html, url):
	if match := re.search(r'https://([\w-]+)\.fanbox\.cc/posts', url):
		author = match.group(1)
		next_page_cache[url] = f"https://api.fanbox.cc/post.paginateCreator?creatorId={author}"
		raise SkipPageError

	if match := re.search(r'https://api\.fanbox\.cc/post\.paginateCreator\?creatorId=(\w+)', url):
		author = match.group(1)
		pages = json.loads(html)["body"]
		next_page_cache[url] = pages[0]
		for i in range(len(pages) - 1):
			next_page_cache[pages[i]] = pages[i + 1]
		raise SkipPageError

	if url.startswith("https://api.fanbox.cc/post.listCreator"):
		posts = json.loads(html)["body"]
		result = []
		for post in posts:
			result.append(Episode(
				url=f"https://{post['creatorId']}.fanbox.cc/posts/{post['id']}",
				title=f"{post['id']} - {(post['title'])}"
				))
		return result[::-1]

	raise TypeError(f"Unknown URL: {url}")

def get_images(html, url):
	if match := re.search(r'https://([\w-]+)\.fanbox\.cc/posts/(\d+)', url):
		# author = match.group(1)
		post_id = match.group(2)
		next_page_cache[url] = f"https://api.fanbox.cc/post.info?postId={post_id}"
		raise SkipPageError

	if match := re.search(r'https://api\.fanbox\.cc/post\.info\?postId=(\d+)', url):
		result = json.loads(html)
		try:
			files = result["body"]["body"]["files"]
		except (KeyError, TypeError):
			raise SkipEpisodeError(always=True) from None
		return [f["url"] for f in files]

	raise TypeError(f"Unknown URL: {url}")
				
def get_next_page(html, url):
	return next_page_cache.pop(url, None)
