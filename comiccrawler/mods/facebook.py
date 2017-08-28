#! python3

"""this is facebook module for comiccrawler

Ex:
	https://www.facebook.com/gtn.moe/photos/pcb.942148229165656/942147902499022/?type=3&theater
	https://www.facebook.com/Nisinsheep/photos/pcb.1667254973516031/1667254333516095/?type=3&theater
	https://www.facebook.com/photo.php?fbid=10202533447211476&set=a.10202533447131474.1073741835.1654599523&type=3&theater
	https://www.facebook.com/photo.php?fbid=10210069591680987&set=p.10210069591680987&type=3&theater

"""

import re, urllib.parse, json
# from urllib.parse import urljoin
from html import unescape
from ..core import Episode, grabhtml
from ..url import urljoin, urlparse, parse_qs

domain = ["www.facebook.com"]
name = "FB"
circular = True
noepfolder = True
config = {
	"cookie_c_user": "",
	"cookie_xs": ""
}

def get_title(html, url):
	try:
		id = re.search(r"photos/([^/]+)", url).group(1)
	except AttributeError:
		id = re.search("set=([^&]+)", url).group(1)
	title = re.search("<title[^>]*>([^<]+)", html).group(1)
	title = re.sub("\s+", " ", title)
	return unescape("{} ({})".format(title, id))

def get_episodes(html, url):
	return [Episode("image", url)]
	
def get_url_info(url):
	try:
		return re.search('photos/([^/]+)/([^/]+)', url).groups()
	except AttributeError:
		pass
	query = urlparse(url).query
	query = parse_qs(query)
	return query["set"], query["fbid"]

def get_images(html, url):
	fbset, fbid = get_url_info(url)
	fb_dtsg = re.search('name="fb_dtsg" value="([^"]+)', html).group(1)
	# fb_dtsg = re.search('"DTSGInitialData".*?"token":"([^"]+?)', html).group(1)
	response = grabhtml(
		"https://www.facebook.com/ajax/photos/snowlift/menu/",
		params={"fbid": fbid, "set": fbset},
		method="POST",
		data={"__a": 1, "fb_dtsg": fb_dtsg}
	)
	# with open("test.js", "w") as f:
		# f.write(response)
	download_url = re.search('"download_photo","href":(.+?),"', response).group(1)
	download_url = json.loads(download_url)
	return urljoin(url, download_url)

def get_next_page(html, url):
	match = re.search('photoPageNextNav"[^>]*?href="([^"]+)', html)
	if match:
		return urllib.parse.urljoin(url, match.group(1))
		
	fbset, fbid = get_url_info(url)
	query = urllib.parse.urlencode({
		"data": json.dumps({"fbid": fbid, "set": fbset}),
		"__a": 1
	})
	pagelet = grabhtml(
		"https://www.facebook.com/ajax/pagelet/generic.php/"
		"PhotoViewerInitPagelet?" + query)
	
	match = re.search(r'"addPhotoFbids".*?(\d+)', pagelet)
	if match:
		next_id = match.group(1)
		return urllib.parse.urljoin(url, "../" + next_id + "/")
	