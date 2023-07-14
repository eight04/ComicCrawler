#! python3

"""
https://linevoom.line.me/user/*
"""

import re, json
from datetime import datetime
from html import unescape
from ..core import Episode
from ..image import Image
from ..url import update_qs
from ..error import LastPageError

domain = ["linevoom.line.me"]
name = "LINE VOOM"
noepfolder = True
config = {
	"curl": ""
	}
autocurl = True
next_page_cache = {}

def get_title(html, url):
	title = re.search("<title[^>]*>([^<]+)", html).group(1)
	title = title.split("|")[0].strip()
	return unescape(f"[LINEVOOM] {title}")

def get_episodes_from_posts(posts):
	result = []
	next_page = "https://linevoom.line.me/api/socialprofile/getPosts?homeId=_ddkO_XiDqCX3mwNJX6Xu6KzM9Qv7Vrvo-uI0UWU&withSocialHomeInfo=false&postId=1168815423900551283&updatedTime=1688154239000&postLimit=10&commentLimit=0&likeLimit=0"
	for post in posts:
		home_id = post["postInfo"]["homeId"]
		id = post["postInfo"]["postId"]
		created_time = post["postInfo"]["createdTime"]
		updated_time = post["postInfo"]["updatedTime"]
		# it is possible that the post has only media
		text = post["contents"].get("text", "")
		images = []
		images.append(Image(
			data={
				"created_time": created_time,
				"text": text
				}
			))
		images.extend(get_medias(post["contents"]["media"]))
		images.extend(get_bound_countent(post["contents"]))
		ep = Episode(
			title=id,
			url=f"https://linevoom.line.me/post/{id}",
			image=images
			)
		next_page = update_qs(next_page, {"homeId": home_id, "postId": id, "updatedTime": updated_time})
		result.append(ep)
	return result, next_page

def get_bound_countent(contents):
	try:
		media = contents["boundContent"]["data"]["media"]["watermark"]["hashedProxyValue"]
	except KeyError:
		return []
	return [media]

def imagehandler(ext, bin):
	if ext == ".json":
		data = json.loads(bin.decode("utf-8"))
		d = datetime.fromtimestamp(data["created_time"] / 1000)
		bin = f"{d:%Y-%m-%d %H:%M:%S}\n\n{data['text']}".encode("utf-8")
		ext = ".txt"
	return ext, bin


def get_episodes(html, url):
	eps = None
	next_page = None

	if "/user/" in url:
		data = re.search('<script id="__NEXT_DATA__" type="application/json">(.+?)</script>', html).group(1)
		data = json.loads(data)
		feeds = data["props"]["pageProps"]["initialState"]["api"]["feeds"]
		eps, next_page = get_episodes_from_posts(feed["post"] for feed in feeds.values())
		next_page_cache[url] = next_page

	else:
		data = json.loads(html)
		if "posts" not in data["data"]:
			raise LastPageError
		eps, next_page = get_episodes_from_posts(data["data"]["posts"])

	next_page_cache[url] = next_page
	eps.reverse()
	return eps

def get_medias(medias):
	for media in medias:
		if media["type"] == "VIDEO":
			if "resourceId" not in media:
				# the video is in boundContent
				continue
			yield f"https://obs.line-scdn.net/{media['resourceId']}/mp4"
		elif media["type"] == "PHOTO":
			yield f"https://obs.line-scdn.net/{media['resourceId']}/m800x1200"
		else:
			raise TypeError(f"Unknown media type: {media['type']}")

def get_next_page(html, url):
	u = next_page_cache.pop(url, None)
	if u:
		return u
