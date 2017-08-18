#! python3

import re
import imghdr
from pprint import pformat
from urllib.parse import quote, urlsplit, urlunsplit
from mimetypes import guess_extension

import requests
from worker import await_, sleep

from ..config import setting
from ..io import content_write
from ..profile import get as profile

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
	scheme, netloc, path, query, _fragment = urlsplit(url)
	return urlunsplit((scheme, netloc, quote_loosely(path), query, ""))

def quote_unicode_dict(d):
	"""Return a safe header, quote the unicode characters."""
	for key, value in d.items():
		d[key] = quote_unicode(value)
	
def grabber_log(*args):
	if setting.getboolean("errorlog"):
		content_write(profile("grabber.log"), pformat(args) + "\n\n", append=True)

sessions = {}
def grabber(url, header=None, *, referer=None, cookie=None, raise_429=True, params=None, done=None, proxy=None):
	"""Request url, return text or bytes of the content."""
	_scheme, netloc, _path, _query, _frag = urlsplit(url)
	
	if netloc not in sessions:
		s = requests.Session()
		s.headers.update(default_header)
		sessions[netloc] = s
	else:
		s = sessions[netloc]
		
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
	r = await_(do_request, s, url, params, proxies, raise_429)
	
	if done:
		done(s, r)
	
	return r
		
def do_request(s, url, params, proxies, raise_429):
	while True:
		r = s.get(url, timeout=20, params=params, proxies=proxies)
		grabber_log(url, r.url, r.request.headers, r.headers)

		if r.status_code == 200:
			break
		if r.status_code != 429 or raise_429:
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
		sleep(5)
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
	if "Content-Type" in r.headers:
		mime = re.search("^(.*?)(;|$)", r.headers["Content-Type"]).group(1)
		mime = mime.strip()

		if mime and mime != "application/octet-stream":
			ext = guess_extension(mime)
			if ext:
				return ext
			
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
