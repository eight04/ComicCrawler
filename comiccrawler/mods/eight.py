#! python3

"""this is 8comic module for comiccrawler.

"""

import re
from urllib.parse import urljoin

from ..safeprint import safeprint
from ..core import Episode

domain = ["www.8comic.com", "www.comicvip.com", "www.comicbus.com"]
name = "無限"

def gettitle(html, url):
	return re.search("<font color=\"#FF6600\" style=\"font:12pt;"
			"font-weight:bold;\">(.+?)</font>",html).group(1)

def getepisodelist(html, url):
	html = html.replace("\n","")
	matches = re.finditer("<a href='#' onclick=\"cview\('(.+?)',(\d+?)\);return "
			"false;\" id=\"\w+?\" class=\"\w+?\">(.+?)</a>", html, re.M)
	s = []
	for match in matches:
		ep_url, catid, title = match.groups()

		# tag cleanup
		title = title.strip()
		title = re.sub("<script.+?</script>","",title)
		title = re.sub("<.+?>","",title)

		catid = int(catid)

		if catid in (3,8,10,11,13,14,15,16,18,20):
			base = "/show/best-manga-"
		else:
			base = "/show/cool-"

		# I have no idea what is this
		# base = "/view/"

		ep_url = ep_url.replace(".html", "").replace("-", ".html?ch=")

		e = Episode(title, urljoin(url, base + ep_url))
		s.append(e)
	return s

def getimgurls(html, url):
	m = re.search("ch=(\d+)", url)
	if m is None:
		ch = "1"
	else:
		ch = m.group(1)

	try:
		# before 2014/4/6
		chs = re.search("chs=(.+?);", html).group(1)
		itemid = re.search("itemid=(.+?);", html).group(1)
		allcodes = re.search("allcodes=\"(.+?)\"", html).group(1)

		cs = allcodes.split("|")
		code = ""

		for c in cs:
			if c.split(" ")[0] == ch:
				code = c
				break
		else:
			raise Exception("can't retrieve imgurl")

		num, sid, did, pages, code = code.split(" ")
		s = []
		for p in range(1, int(pages)+1):
			hash = (((p - 1) // 10) % 10) + (((p - 1) % 10) * 3)
			s.append("http://img" + sid + ".8comic.com/" + did + "/" + itemid + "/" + num + "/" + "{:03}_{}".format(p, code[hash:hash+3]) + ".jpg")
		return s
	except Exception:
		pass

	# after 2014/4/6
	def ss(str):
		return re.sub("[a-z]+", "", str)

	cs = re.search("cs='(.+)'", html).group(1)
	ti = re.search("ti=(\d+);", html).group(1)

	i = 0
	while i < len(cs):
		if ch == ss(cs[i:i+4]):
			code = cs[i:i+50]
			break
		i += 50
	else:
		code = cs[-50:]

	pages = int(ss(code[7:10]))

	s = []
	for p in range(1, pages + 1):
		hash = (((p - 1) // 10) % 10) + (((p - 1) % 10) * 3)
		src = "http://img{}.8comic.com/{}/{}/{}/{:03}_{}.jpg".format(
				ss(code[4:6]), code[6:7], ti, ch, p, code[hash + 10:hash + 13])
		s.append(src)
	return s
