#! python3

from collections import namedtuple
from contextlib import contextmanager
from pathlib import Path
from threading import Lock
from urllib.parse import quote, urlsplit, urlunsplit, urlparse
import re
# import socket
import time
import json

from worker import async_, await_, sleep, Defer
# from urllib3.util import is_fp_closed
from urllib3.exceptions import IncompleteRead
from curl_cffi.requests.exceptions import HTTPError

from .config import setting
from .io import content_write
from .profile import get as profile
from .session_manager import session_manager
from .filename_ext import get_ext
from .channel import request_ch

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

def grabber_log(obj):
	if setting.getboolean("errorlog"):
		content = time.strftime("%Y-%m-%dT%H:%M:%S%z") + "\n" + json.dumps(obj, indent=2, sort_keys=True) + "\n\n"
		content_write(profile("grabber.log"), content, append=True)

inc_request_id = 1

def grabber(url, *, referer=None, retry=False, done=None, proxy=None, **kwargs):
	"""Request url, return text or bytes of the content."""
	s = session_manager.get(url)

	if referer:
		s.headers['Referer'] = quote_unicode(referer)

	if isinstance(proxy, str):
		proxies = {'http': proxy, 'https': proxy}
	else:
		proxies = proxy

	r = await_(do_request, s, url, proxies, retry, **kwargs)

	if done:
		done(s, r)

	global inc_request_id
	r.request_id = inc_request_id
	inc_request_id += 1

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
			break
		if not retry or r.status_code not in RETRYABLE_HTTP_CODES:
			try: 
				# FIXME: https://github.com/lexiforest/curl_cffi/issues/467
				r.raise_for_status()
			except HTTPError as err:
				if not err.response:
					err.response = r
				raise err
		# 302 error without location header
		if r.status_code == 302:
			# pylint: disable=protected-access
			raise TypeError("status 302 without location header")
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

def iter_content(r):
	"""Iterate the content of the response."""
	yield from r.iter_content()

RequestProgress = namedtuple("RequestProgress", "id loaded total hostname", defaults=(None, None, None))

def grabimg(*args, on_opened=None, tempfile=None, headers=None, **kwargs):
	"""Grab the image. Return ImgResult"""
	kwargs["stream"] = True
	loaded = 0
	if tempfile:
		try:
			loaded = Path(tempfile).stat().st_size
		except FileNotFoundError:
			pass
	if loaded:
		if not headers:
			headers = {}
		headers["Range"] = f"bytes={loaded}-"
	try:
		r = grabber(*args, headers=headers, **kwargs)
	except HTTPError as err:
		if err.response.status_code != 416:
			raise err
		try:
			content_range_max = int(err.response.headers["Content-Range"].split("/")[-1])
		except (KeyError, ValueError) as err_no_content_range:
			raise err from err_no_content_range
		if content_range_max == loaded:
			# NOTE: we create a new request for metadata since the server may return wrong metadata on 416 resopnses
			h = headers.copy()
			del h["Range"]
			r = grabber(*args, headers=h, **kwargs, method="HEAD")
			return ImgResult(r, tempfile=tempfile)
		if content_range_max < loaded and tempfile:
			# FIXME: this should not happen
			Path(tempfile).unlink()
		raise err
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
			request_ch.pub("REQUEST_START", data=RequestProgress(id=r.request_id, loaded=loaded, total=total, hostname=u.hostname))
			if tempfile:
				Path(tempfile).parent.mkdir(parents=True, exist_ok=True)
				mode = "ab" if loaded else "wb"
				with open(tempfile, mode=mode) as f:
					for chunk in iter_content(r):
						f.write(chunk)
						loaded += len(chunk)
						request_ch.pub("REQUEST_PROGRESS", data=RequestProgress(id=r.request_id, loaded=loaded))
			else:
				for chunk in iter_content(r):
					content_list.append(chunk)
					loaded += len(chunk)
					request_ch.pub("REQUEST_PROGRESS", data=RequestProgress(id=r.request_id, loaded=loaded))
	finally:
		# FIXME: is it safe to always close the connection?
		request_ch.pub("REQUEST_END", data=RequestProgress(id=r.request_id))
		r.close()
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
