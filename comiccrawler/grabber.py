#! python3

import re
import time
from contextlib import contextmanager
from pprint import pformat
from threading import Lock
from urllib.parse import quote, urlsplit, urlunsplit
from mimetypes import guess_extension
import socket

import enlighten
import requests
import puremagic
from worker import WorkerExit, async_, await_, sleep, Defer

from .config import setting
from .io import content_write
from .profile import get as profile
from .session_manager import session_manager

default_header = {
	"User-Agent": "Mozilla/5.0 (Windows NT 6.3; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.99 Safari/537.36",
	"Accept-Language": "zh-tw,zh;q=0.8,en-us;q=0.5,en;q=0.3",
	"Accept-Encoding": "gzip, deflate"
	}

cooldown = {}
grabber_pool = {}
grabber_pool_lock = Lock()
pb_manager = enlighten.get_manager()

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

def grabber(url, header=None, *, referer=None, cookie=None,
			retry=False, done=None, proxy=None, **kwargs):
	"""Request url, return text or bytes of the content."""
	s = session_manager.get(url)

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
			r = s.request(kwargs.pop("method", "GET"), url, timeout=(22, 60),
				 proxies=proxies, **kwargs)
		grabber_log(url, r.url, r.request.headers, r.headers)

		if r.status_code == 200:
			content_length = r.headers.get("Content-Length")
			if not kwargs.get("stream", False) and content_length and int(content_length) != r.raw.tell():
				raise ValueError(
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
				raise TypeError("status 302 without location header")
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

def _get_ext(r, b):
	"""Get file extension"""
	# FIXME: should we read the disk and guess the extension?
	if b:
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

	# FIXME: should we read b from disk?
	if not mime and b:
		filename = urlsplit(r.url).path
		mime = puremagic.from_string(b, mime=True, filename=filename)

	if mime:
		ext = guess_extension(mime)
		if ext:
			return ext
		# guess_extension doesn't handle video/x-m4v
		match = re.match(r"\w+/x-(\w+)$", mime)
		if match:
			return f".{match.group(1)}"

def get_ext(r, b):
	"""Get file extension"""
	ext = _get_ext(r, b)
	# some mapping
	if ext in (".jpeg", ".jpe"):
		return ".jpg"
	return ext

def grabimg(*args, on_opened=None, tempfile=None, range=False, header=None, **kwargs):
	"""Grab the image. Return ImgResult"""
	kwargs["stream"] = True
	if range and tempfile:
		try:
			loaded = Path(tempfile).stat().st_size
		except FileNotFoundError:
			loaded = 0
		if not header
			header = {}
		header["Range"] = f"bytes={loaded}-"
	else:
		loaded = 0
	r = grabber(*args, header=header, **kwargs)
	if on_opened:
		on_opened(r)
	if range and r.status_code != 206:
		loaded = 0
		Path(tempfile).unlink(missing_ok=True)
		print(f"WARNING: server does not support range request: {r.url}")
	total = int(r.headers.get("Content-Length", "0")) or None
	content_list = []
	try:
		@await_
		def _():
			with pb_manager.counter(total=total, unit="b", leave=False) as counter:
				if tempfile:
					with open(tempfile, "ab") as f:
						for chunk in r.iter_content(chunk_size=None):
							f.write(chunk)
							counter.update(len(chunk))
				else:
					for chunk in r.iter_content(chunk_size=None):
						content_list.append(chunk)
						counter.update(len(chunk))
			r._content = b"".join(content_list) # pylint: disable=protected-access
	except WorkerExit:
		socket.close(r.raw._fp.fileno())
		r.raw.release_conn()
		raise
	b = None
	if content_list:
		b = b"".join(content_list)
	return ImgResult(r, tempfile=tempfile, b=b)

class ImgResult:
	def __init__(self, response, tempfile=None, b=None):
		self.response = response
		self.ext = get_ext(response, b)
		self.bin = b
