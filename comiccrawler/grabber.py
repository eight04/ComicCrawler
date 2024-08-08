#! python3

from contextlib import contextmanager
from email.message import EmailMessage
from pathlib import Path
from threading import Lock
from urllib.parse import quote, urlsplit, urlunsplit, urlparse
import re
import socket
import time
import json

import enlighten
import requests
import puremagic
from worker import WorkerExit, async_, await_, sleep, Defer
from urllib3.util import is_fp_closed
from urllib3.exceptions import IncompleteRead

from .config import setting
from .io import content_write
from .profile import get as profile
from .session_manager import session_manager

cooldown = {}
grabber_pool = {}
grabber_pool_lock = Lock()
pb_manager = enlighten.get_manager()

mime_dict = {
	t.mime_type: t for t in puremagic.magic_header_array
	}

def ext_from_mime(mime):
	mime = mime.lower().strip()
	try:
		return mime_dict[mime].extension
	except KeyError:
		return None

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

def grabber_log(obj):
	if setting.getboolean("errorlog"):
		content = time.strftime("%Y-%m-%dT%H:%M:%S%z") + "\n" + json.dumps(obj, indent=2, sort_keys=True) + "\n\n"
		content_write(profile("grabber.log"), content, append=True)

def grabber(url, header=None, *, referer=None, cookie=None,
			retry=False, done=None, proxy=None, **kwargs):
	"""Request url, return text or bytes of the content."""
	s = session_manager.get(url)

	if referer:
		s.headers['Referer'] = quote_unicode(referer)

	if cookie:
		quote_unicode_dict(cookie)
		requests.utils.add_dict_to_cookiejar(s.cookies, cookie)

	if isinstance(proxy, str):
		proxies = {'http': proxy, 'https': proxy}
	else:
		proxies = proxy

	r = await_(do_request, s, url, proxies, retry, headers=header, **kwargs)

	if done:
		done(s, r)

	return r

RETRYABLE_HTTP_CODES = (423, 429, 503)
SUCCESS_CODES = (200, 206)

def do_request(s, url, proxies, retry, **kwargs):
	sleep_time = 5
	while True:
		with get_request_lock(url):
			r = s.request(kwargs.pop("method", "GET"), url, proxies=proxies, **kwargs)
		for r2 in (r.history + [r]):
			grabber_log({
				"status_code": r2.status_code,
				"url": r2.url,
				"request_headers": dict(r2.request.headers),
				"response_headers": dict(r2.headers),
				"json": kwargs.get("json"),
				})

		if r.status_code in SUCCESS_CODES:
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

def get_filename_from_response(r):
	msg = EmailMessage()
	for key, value in r.headers.items():
		msg.add_header(key, value)
	return msg.get_filename()

def _get_ext(r, b, tempfile):
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

	if filename := get_filename_from_response(r):
		if suffix := Path(filename).suffix:
			return suffix

	mime = None
	if "Content-Type" in r.headers:
		mime = re.search("^(.*?)(;|$)", r.headers["Content-Type"]).group(1)
		mime = mime.strip()
		if "octet-stream" in mime:
			mime = None

	if mime:
		ext = ext_from_mime(mime)
		if ext:
			return ext

		# FIXME: is it safe to handle x-? like this?
		# video/x-m4v
		match = re.match(r"\w+/x-(\w+)$", mime)
		if match:
			return f".{match.group(1)}"

	if b:
		filename = urlsplit(r.url).path
		return puremagic.from_string(b, filename=filename)

	if tempfile:
		return puremagic.from_file(tempfile)


def get_ext(r, b, tempfile):
	"""Get file extension"""
	ext = _get_ext(r, b, tempfile)
	# some mapping
	if ext in (".jpeg", ".jpe"):
		return ".jpg"
	# https://github.com/cdgriffith/puremagic/issues/3
	if ext == ".docx":
		return ".zip"
	return ext

def iter_content(r):
	"""Iterate the content of the response."""
	# FIXME: requests streaming is so broken wtf
	# https://github.com/psf/requests/issues/5536
	# https://github.com/urllib3/urllib3/issues/2123
	if r.raw.chunked and r.raw.supports_chunked_reads():
		yield from r.raw.read_chunked(decode_content=True)
	else:
		while not is_fp_closed(r.raw._fp) or len(r.raw._decoded_buffer) > 0: # pylint: disable=protected-access
			b = r.raw.read1(decode_content=True)
			yield b
			if not b:
				sleep(0.1)

def grabimg(*args, on_opened=None, tempfile=None, header=None, **kwargs):
	"""Grab the image. Return ImgResult"""
	kwargs["stream"] = True
	loaded = 0
	if tempfile:
		try:
			loaded = Path(tempfile).stat().st_size
		except FileNotFoundError:
			pass
	if loaded:
		if not header:
			header = {}
		header["Range"] = f"bytes={loaded}-"
	r = grabber(*args, header=header, **kwargs)
	if on_opened:
		on_opened(r)
	if r.status_code == 200:
		loaded = 0
	total = int(r.headers.get("Content-Length", "0")) + loaded or None
	content_list = []
	try:
		@await_
		def _():
			nonlocal loaded
			u = urlparse(r.url)
			with pb_manager.counter(total=total, unit="b", leave=False, desc=u.hostname) as counter:
				counter.update(loaded)
				if tempfile:
					Path(tempfile).parent.mkdir(parents=True, exist_ok=True)
					mode = "ab" if loaded else "wb"
					with open(tempfile, mode=mode) as f:
						for chunk in iter_content(r):
							f.write(chunk)
							counter.update(len(chunk))
							loaded += len(chunk)
				else:
					for chunk in iter_content(r):
						content_list.append(chunk)
						counter.update(len(chunk))
						loaded += len(chunk)
	except WorkerExit:
		socket.close(r.raw._fp.fileno()) # pylint: disable=protected-access
		r.raw.release_conn()
		raise
	if total and loaded < total:
		raise IncompleteRead(loaded, total - loaded)
	b = None
	if content_list:
		b = b"".join(content_list)
	return ImgResult(r, tempfile=tempfile, b=b)

class ImgResult:
	def __init__(self, response, tempfile=None, b=None):
		self.response = response
		self.ext = get_ext(response, b, tempfile)
		self.bin = b
