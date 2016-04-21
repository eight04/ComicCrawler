#! python3

import gzip
import re

from urllib.parse import quote, urlsplit, urlunsplit
from urllib.request import Request, urlopen
from urllib.error import HTTPError

from http.cookies import SimpleCookie

from worker import sync, sleep
from pprint import pformat

from ..config import setting
from ..io import content_write

default_header = {
	"User-Agent": "Mozilla/5.0 (Windows NT 6.1; WOW64; rv:34.0) Gecko/20100101 Firefox/34.0",
	"Accept-Language": "zh-tw,zh;q=0.8,en-us;q=0.5,en;q=0.3",
	"Accept-Encoding": "gzip, deflate"
}

def quote_unicode(s):
	"""Quote unicode characters only."""
	return quote(s, safe=r"/ !\"#$%&'()*+,:;<=>?@[\\]^`{|}~")

def quote_loosely(s):
	"""Quote space and others in path part.

	Reference:
	  http://stackoverflow.com/questions/120951/how-can-i-normalize-a-url-in-python
	"""
	return quote(s, safe="%/:=&?~#+!$,;'@()*[]")

def safeurl(url):
	"""Return a safe url, quote the unicode characters.

	This function should follow this rule:
	  safeurl(safeurl(url)) == safe(url)
	"""
	scheme, netloc, path, query, fragment = urlsplit(url)
	return urlunsplit((scheme, netloc, quote_loosely(path), query, ""))

def safeheader(header):
	"""Return a safe header, quote the unicode characters."""
	for key, value in header.items():
		if not isinstance(value, str):
			raise Exception(
				"header value must be str!\n" + pformat(header)
			)
		header[key] = quote_unicode(value)
	return header

cookiejar = {}
def grabber(url, header=None, *, referer=None, cookie=None, raw=False, errorlog=None):
	"""Request url, return text or bytes of the content."""

	url = safeurl(url)

	print("[grabber]", url, "\n")

	# Build request
	request = Request(url)

	# Build header
	if header is None:
		header = {}

	# Build default header
	for key in default_header:
		if key not in header:
			header[key] = default_header[key]

	# Referer
	if referer:
		header["Referer"] = referer

	# Handle cookie
	if request.host not in cookiejar:
		cookiejar[request.host] = SimpleCookie()

	jar = cookiejar[request.host]

	if cookie:
		jar.load(cookie)

	if "Cookie" in header:
		jar.load(header["Cookie"])

	if jar:
		header["Cookie"] = "; ".join([key + "=" + c.value for key, c in jar.items()])

	header = safeheader(header)
	for key, value in header.items():
		request.add_header(key, value)

	response = None
	while not response:
		try:
			response = urlopen(request, timeout=20)
		except HTTPError as err:
			if err.code == 429:
				retry = 20
				for key, value in err.headers.items():
					if key == "Retry-After":
						retry = int(value)
						break
				sleep(retry)
			else:
				raise

	jar.load(response.getheader("Set-Cookie", ""))
	if cookie is not None:
		for key, c in jar.items():
			cookie[key] = c.value

	b = response.read()

	# decompress gziped data
	if response.getheader("Content-Encoding") == "gzip":
		b = gzip.decompress(b)

	if raw:
		content = b

	else:
		# find html defined encoding
		s = b.decode("utf-8", "replace")
		match = re.search(r"charset=[\"']?([^\"'>]+)", s)
		if match:
			s = b.decode(match.group(1), "replace")
		content = s

	if setting.getboolean("errorlog"):
		log_object = (
			url,
			request.header_items(),
			response.getheaders()
		)
		if not errorlog:
			errorlog = ""
		content_write("~/comiccrawler/grabber.log", pformat(log_object) + "\n\n", append=True)

	return content

def grabhtml(*args, **kwargs):
	"""Get html source of given url. Return String."""
	kwargs["raw"] = False
	return sync(grabber, *args, **kwargs)

def grabimg(*args, **kwargs):
	"""Return byte array."""
	kwargs["raw"] = True
	return sync(grabber, *args, **kwargs)
