#! python3

import gzip
import re
import requests

from urllib.parse import quote, urlsplit, urlunsplit
from urllib.request import Request, urlopen
from mimetypes import guess_extension

from http.cookies import SimpleCookie

from requests.exceptions import HTTPError

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

def quote_unicode_dict(d):
	"""Return a safe header, quote the unicode characters."""
	for key, value in d.items():
		d[key] = quote_unicode(value)
	
def grabber_log(*args):
	content_write("~/comiccrawler/grabber.log", pformat(args) + "\n\n", append=True)

sessions = {}
def grabber(url, header=None, *, referer=None, cookie=None):
	"""Request url, return text or bytes of the content."""
	scheme, netloc, path, query, frag = urlsplit(url)
	
	if netloc not in sessions:
		s = requests.Session()
		s.headers.update(default_header)
		sessions[netloc] = s
	else:
		s = sessions[netloc]
		
	if header:
		s.headers.update(header)

	if referer:
		s.headers['referer'] = referer

	if cookie:
		quote_unicode_dict(cookie)
		requests.utils.add_dict_to_cookiejar(s.cookies, cookie)

	r = s.get(url, timeout=20)

	if setting.getboolean("errorlog"):
		grabber_log(url, r.request.headers, r.headers)

	if r.status_code != 200:
		r.raise_for_status()
			
	return r
	
def is_429(err):
	"""Return True if it is a 429 HTTPError"""
	if isinstance(err, requests.HTTPError) and hasattr(err, "response"):
		return err.response.status_code == 429
	return False
			
def grabhtml(*args, **kwargs):
	"""Get html source of given url. Return String."""
	r = sync(grabber, *args, **kwargs)
	
	# decode to text
	match = re.search(br"charset=[\"']?([^\"'>]+)", r.content)
	if match:
		r.encoding = match.group(1).decode("latin-1")
		
	return r.text

def grabimg(*args, **kwargs):
	"""Return byte array."""
	r = sync(grabber, *args, **kwargs)
	
	# find extension
	ext = None
	if "Content-Type" in r.headers:
		mime = re.search("^(.*?)(;|$)", r.headers["Content-Type"]).group(1)
		mime = mime.strip()
		ext = guess_extension(mime)
	return ext, r.content
