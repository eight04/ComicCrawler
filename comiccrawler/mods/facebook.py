#! python3

"""this is facebook module for comiccrawler

Ex:
	https://www.facebook.com/gtn.moe/photos/pcb.942148229165656/942147902499022/?type=3&theater
	https://www.facebook.com/Nisinsheep/photos/pcb.1667254973516031/1667254333516095/?type=3&theater
	https://www.facebook.com/photo.php?fbid=10202533447211476&set=a.10202533447131474.1073741835.1654599523&type=3&theater
	https://www.facebook.com/photo.php?fbid=10210069591680987&set=p.10210069591680987&type=3&theater

"""

import re, json
from html import unescape
from ..core import Episode

domain = ["www.facebook.com"]
name = "FB"
circular = True
noepfolder = True
config = {
	"curl": ""
}
autocurl = True

def get_title(html, url):
	try:
		id = re.search(r"photos/([^/]+)", url).group(1)
	except AttributeError:
		id = re.search("set=([^&]+)", url).group(1)
	title = re.search("<title[^>]*>([^<]+)", html).group(1)
	title = re.sub(r"\s+", " ", title)
	return unescape("{} ({})".format(title, id))

def get_episodes(html, url):
	return [Episode("image", url)]
	
def get_images(html, url):
	# with open("test.html", "w", encoding="utf-8") as f:
	# 	f.write(html)
	i = html.index("currMedia")
	rx = re.compile(r'"image":\{"uri":("[^"]+")')
	uri = rx.search(html, i).group(1)
	uri = json.loads(uri)
	return [uri]

def get_next_image_page(html, url):
	i = html.index("nextMediaAfterNodeId")
	rx = re.compile(r'"id":"([^"]+)"')
	next_id = rx.search(html, i).group(1)
	return get_next_url(url, next_id)

def get_next_url(url, next_id):
	match = re.match(r'(https://www\.facebook\.com/[^/]+/photos/[^/]+/)\d+(.*)', url)
	if match:
		return match.group(1) + next_id + match.group(2)

	match = re.match(r'(.*fbid=)\d+(.*)', url)
	if match:
		return match.group(1) + next_id + match.group(2)

	raise TypeError("Can't find next url")
