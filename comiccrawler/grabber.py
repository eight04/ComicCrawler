#! python3

import re
import time
import imghdr
from contextlib import contextmanager
from pprint import pformat
from threading import Lock
from urllib.parse import quote, urlsplit, urlunsplit
from mimetypes import guess_extension

import requests
import puremagic
from worker import async_, await_, sleep, Defer

from .config import setting
from .io import content_write
from .profile import get as profile

default_header = {
	"User-Agent": "Mozilla/5.0 (Windows NT 6.3; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.99 Safari/537.36",
	"Accept-Language": "zh-tw,zh;q=0.8,en-us;q=0.5,en;q=0.3",
	"Accept-Encoding": "gzip, deflate"
}

cooldown = {}
grabber_pool = {}
grabber_pool_lock = Lock()

@contextmanager
def get_request_lock(url):
	domain = urlsplit(url).hostname
	defer = Defer()
	try:
		with grabber_pool_lock:
			last_defer = grabber_pool.get(domain)
			grabber_pool[domain] = defer
		if last_defer:
			last_defer.get()
		yield
	finally:
		@async_
		def _():
			time.sleep(cooldown.get(domain, 0))
			defer.resolve(None)

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
	scheme, netloc, path, query, _fragment = urlsplit(url)
	return urlunsplit((scheme, netloc, quote_loosely(path), query, ""))

def quote_unicode_dict(d):
	"""Return a safe header, quote the unicode characters."""
	for key, value in d.items():
		d[key] = quote_unicode(value)
	
def grabber_log(*args):
	if setting.getboolean("errorlog"):
		content = time.strftime("%Y-%m-%dT%H:%M:%S%z") + "\n" + pformat(args) + "\n\n"
		content_write(profile("grabber.log"), content, append=True)

def get_session(netloc):
	s = None
	if netloc not in sessions:
		s = requests.Session()
		s.headers.update(default_header)
		sessions[netloc] = s
	else:
		s = sessions[netloc]
	return s
	

sessions = {}
def grabber(url, header=None, *, referer=None, cookie=None,
		retry=False, done=None, proxy=None, **kwargs):
	"""Request url, return text or bytes of the content."""
	_scheme, netloc, _path, _query, _frag = urlsplit(url)
	
	s = get_session(netloc)
		
	if header:
		s.headers.update(header)

	if referer:
		s.headers['referer'] = quote_unicode(referer)

	if cookie:
		quote_unicode_dict(cookie)
		requests.utils.add_dict_to_cookiejar(s.cookies, cookie)

	if isinstance(proxy, str):
		proxies = {'http': proxy, 'https': proxy}
	else:
		proxies = proxy
		
	r = await_(do_request, s, url, proxies, retry, **kwargs)
	
	if done:
		done(s, r)
	
	return r
	
RETRYABLE_HTTP_CODES = (423, 429, 503)
	
def do_request(s, url, proxies, retry, **kwargs):
	sleep_time = 5
	while True:
		with get_request_lock(url):
			r = s.request(kwargs.pop("method", "GET"), url, timeout=20,
				proxies=proxies, **kwargs)
		grabber_log(url, r.url, r.request.headers, r.headers)

		if r.status_code == 200:
			content_length = r.headers.get("Content-Length")
			if content_length and int(content_length) != r.raw.tell():
				raise Exception(
					"incomplete response. Content-Length: {content_length}, got: {actual}"
						.format(content_length=content_length, actual=r.raw.tell())
				)
			break
		if not retry or r.status_code not in RETRYABLE_HTTP_CODES:
			r.raise_for_status()
		# 302 error without location header
		if r.status_code == 302:
			# pylint: disable=protected-access
			match = re.search(
				r"^location:\s*(.+)",
				str(r.raw._original_response.msg),
				re.M + re.I
			)
			if not match:
				raise Exception("status 302 without location header")
			url = match.group(1)
			continue
		print(r)
		print("retry after {sleep_time} seconds".format(sleep_time=sleep_time))
		sleep(sleep_time)
		sleep_time *= 2
	return r
	
def grabhtml(*args, **kwargs):
	"""Get html source of given url. Return String."""
	r = grabber(*args, **kwargs)
	guess_encoding(r)
	return r.text

def guess_encoding(r):
	# decode to text
	match = re.search(br"charset=[\"']?([^\"'>]+)", r.content)
	if match:
		encoding = match.group(1).decode("latin-1")
		if encoding == "gb2312":
			encoding = "gbk"
		r.encoding = encoding
	
def _get_ext(r):
	"""Get file extension"""
	b = r.content
	ext = imghdr.what("", b)
	if ext:
		return "." + ext

	# imghdr issue: http://bugs.python.org/issue16512
	if b[:2] == b"\xff\xd8":
		return ".jpg"
		
	# http://www.garykessler.net/library/file_sigs.html
	if b[:4] == b"\x1a\x45\xdf\xa3":
		return ".webm"
		
	if b[:4] == b"RIFF" and b[8:12] == b"WEBP":
		return ".webp"
		
	if b[:4] == b"8BPS":
		return ".psd"
		
	if (b[:16] == b"\x30\x26\xB2\x75\x8E\x66\xCF\x11"
			b"\xA6\xD9\x00\xAA\x00\x62\xCE\x6C"):
		return ".wmv"
		
	mime = None
	if "Content-Type" in r.headers:
		mime = re.search("^(.*?)(;|$)", r.headers["Content-Type"]).group(1)
		mime = mime.strip()
		if "octet-stream" in mime:
			mime = None

	if not mime:
		filename = urlsplit(r.url).path
		mime = puremagic.from_string(b, mime=True, filename=filename)
	
	if mime:
		ext = guess_extension(mime)
		if ext:
			return ext
		# guess_extension doesn't handle video/x-m4v
		match = re.match("\w+/x-(\w+)$", mime)
		if match:
			return f".{match.group(1)}"
		
def get_ext(r):
	"""Get file extension"""
	ext = _get_ext(r)
	# some mapping
	if ext in (".jpeg", ".jpe"):
		return ".jpg"
	return ext

def grabimg(*args, **kwargs):
	"""Grab the image. Return ImgResult"""
	return ImgResult(grabber(*args, **kwargs))

class ImgResult:
	def __init__(self, response):
		self.response = response
		self.ext = get_ext(response)
		self.bin = response.content
