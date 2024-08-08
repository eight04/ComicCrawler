#! python3

"""twitter"""

import re
import json

from collections import OrderedDict
from urllib.parse import urlparse, parse_qs

from ..episode import Episode
from ..grabber import grabber
from ..url import update_qs
from ..error import is_http, SkipEpisodeError
from ..session_manager import session_manager
from ..util import get_cookie

domain = ["twitter.com", "x.com"]
name = "twitter"
config = {
	"curl": ""
}
noepfolder = True

next_page_cache = {}
pin_entry_cache = {}

AUTH = "AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA"

def get_title(html, url):
	name = re.search(r"\.com/([^/]+)", url).group(1)
	if is_media(url):
		return f"[twitter] {name} (media)"
	return f"[twitter] {name}"

def session_key(url):
	r = urlparse(url)
	if r.path.startswith("/i/api"):
		return (r.scheme, r.netloc, "/i/api")
	
def is_media(url):
	if re.search(r"\.com/[^/]+/media", url):
		return True
	if re.search(r"graphql/[^/]+/UserMedia", url):
		return True
	return False

def init_api_session():
	session = session_manager.get("https://x.com/i/api/")
	session.headers.update({
		"authorization": f"Bearer {AUTH}",
		"x-csrf-token": get_cookie(session.cookies, "ct0", domain="x.com"),
		"x-twitter-active-user": "yes",
		"x-twitter-auth-type": "OAuth2Session",
		"x-twitter-client-language": "en"
		})

def get_episodes(html, url):
	init_api_session()
	name = re.search(r"\.com/([^/]+)", url).group(1)
	if name != "i":
		variables = {
			"screen_name": name,
			"withSafetyModeUserFields": True,
			"withSuperFollowsUserFields": False
		}
		u = update_qs(
			"https://x.com/i/api/graphql/LPilCJ5f-bs3MjJJNcuuOw/UserByScreenName",
			{"variables": json.dumps(variables)}
		)
		result = grabber(u).json()
		uid = result["data"]["user"]["result"]["rest_id"]
		
		endpoint = user_media_graph if is_media(url) else user_tweets_graph
		next_page_cache[url] = endpoint(userId=uid)
		return
		
	if any(k in url for k in ["UserTweets", "UserMedia"]):
		data = json.loads(html)
		instructions = data["data"]["user"]["result"]["timeline"]["timeline"]["instructions"]
		for instruction in reversed(instructions):
			# FIXME: we have to process pin entry first
			if instruction["type"] == "TimelinePinEntry":
				extract_pin_entry(instruction["entry"], url)
			
			if instruction["type"] == "TimelineAddEntries":
				yield from reversed(list(extract_added_entries(instruction["entries"], url)))
				
def tweet_result_to_episode(tweet_result):
	try:
		legacy = tweet_result["legacy"]
	except KeyError:
		legacy = tweet_result["tweet"]["legacy"]
	
	try:
		all_media = legacy["entities"]["media"] + legacy["extended_entities"]["media"]
	except KeyError:
		return None
	imgs = [find_media_source(m) for m in all_media]
	imgs = list(OrderedDict.fromkeys(imgs).keys()) # remove dup
	result = None

	try:
		result = tweet_result["legacy"]["retweeted_status_result"]["result"]
	except KeyError:
		result = tweet_result
	try:
		core = result["core"]
	except KeyError:
		core = result["tweet"]["core"]
	screen_name = core["user_results"]["result"]["legacy"]["screen_name"]

	try:
		legacy = result["legacy"]
	except KeyError:
		legacy = result["tweet"]["legacy"]
	id_str = legacy["id_str"]	

	ep_url = f"https://x.com/{screen_name}/status/{id_str}"
	
	return Episode(
		title=id_str,
		url=ep_url,
		image=imgs
	)

def extract_pin_entry(entry, url):
	ep = tweet_result_to_episode(entry["content"]["itemContent"]["tweet_results"]["result"])
	if not ep:
		return
	user_id = parse_graph_variable(url)["userId"]
	pin_entry_cache[(user_id, is_media(url))] = ep

def extract_added_entries(entries, url):
	user_id = parse_graph_variable(url)["userId"]
	pin_entry_key = (user_id, is_media(url))
	pinned_entry = pin_entry_cache.get(pin_entry_key)
	cursor = None
	has_timeline = False
	
	for entry in entries:
		if entry["content"]["entryType"] == "TimelineTimelineItem":
			has_timeline = True
			if "result" not in entry["content"]["itemContent"]["tweet_results"]:
				# deleted post?
				continue
			ep = tweet_result_to_episode(entry["content"]["itemContent"]["tweet_results"]["result"])
			if not ep:
				continue
				
			if pinned_entry and url_to_id(pinned_entry.url) > url_to_id(ep.url):
				yield pinned_entry
				del pin_entry_cache[pin_entry_key]
				pinned_entry = None
				
			yield ep
			
		if entry["content"]["entryType"] == "TimelineTimelineCursor" and entry["content"]["cursorType"] == "Bottom":
			cursor = entry["content"]["value"]
				
	if cursor and has_timeline:
		endpoint = user_media_graph if is_media(url) else user_tweets_graph
		next_page_cache[url] = endpoint(userId=user_id, cursor=cursor)
		
	if not has_timeline and pinned_entry:
		yield pinned_entry
		del pin_entry_cache[pin_entry_key]

def url_to_id(url):
	tid = re.search(r"\d+$", url).group()
	return int(tid)
	
def find_media_source(media):
	if media["type"] == "video":
		max_video = sorted(media["video_info"]["variants"], key=lambda i: i.get("bitrate", 0)).pop()
		return max_video["url"]
	return media["media_url_https"] + ":orig"
	
def parse_graph_variable(url):
	variables = parse_qs(urlparse(url).query)["variables"][0]
	return json.loads(variables)
	
def user_tweets_graph(**kwargs):
	variables = {
		"count": 20,
		"withTweetQuoteCount": True,
		"includePromotedContent": True,
		"withSuperFollowsUserFields": False,
		"withUserResults": True,
		"withBirdwatchPivots": False,
		"withReactionsMetadata": False,
		"withReactionsPerspective": False,
		"withSuperFollowsTweetFields": False,
		"withVoice": True
	}
	variables.update(kwargs)
	return update_qs(
		"https://x.com/i/api/graphql/PIt4K9PnUM5DP9KW_rAr0Q/UserTweets",
		{"variables": json.dumps(variables)}
	)
	
def user_media_graph(**kwargs):
	variables = {
		"userId": "1240968347375656960",
		"count": 20,
		"withHighlightedLabel": True,
		"withTweetQuoteCount": False,
		"includePromotedContent": False,
		"withSuperFollowsUserFields": False,
		"withUserResults": True,
		"withBirdwatchPivots": False,
		"withReactionsMetadata": True,
		"withReactionsPerspective": True,
		"withSuperFollowsTweetFields": False,
		"withClientEventToken": False,
		"withBirdwatchNotes": False,
		"withVoice": True
	}
	variables.update(kwargs)
	return update_qs(
		"https://x.com/i/api/graphql/JWaFyG5p4-UvSyxGMe15-g/UserMedia",
		{"variables": json.dumps(variables)}
	)

def tweet_detail_graph(**kwargs):
	variables = {"focalTweetId":"1438138335042564102","with_rux_injections":False,"includePromotedContent":True,"withCommunity":True,"withQuickPromoteEligibilityTweetFields":True,"withTweetQuoteCount":True,"withBirdwatchNotes":False,"withSuperFollowsUserFields":True,"withBirdwatchPivots":False,"withDownvotePerspective":False,"withReactionsMetadata":False,"withReactionsPerspective":False,"withSuperFollowsTweetFields":True,"withVoice":True,"withV2Timeline":False,"__fs_interactive_text":False,"__fs_dont_mention_me_view_api_enabled":False}
	variables.update(kwargs)
	return update_qs(
		"https://x.com/i/api/graphql/s2RO46g9Rhw53GX2BEMfiA/TweetDetail",
		{"variables": json.dumps(variables)}
	)

def errorhandler(err, crawler):
	if is_http(err, 404):
		tid = re.search(r"status/(\d+)", crawler.ep.current_url).group(1)
		u = tweet_detail_graph(focalTweetId=tid)
		r = grabber(u).json()
		if r.get("errors", None):
			if "No status found" in r["errors"][0]["message"]:
				raise SkipEpisodeError(always=True)

def get_next_page(html, url):
	return next_page_cache.pop(url, None)
