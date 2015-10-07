#! python3

from imghdr import what
from os import mkdir, listdir
from os.path import normpath, split, join
from re import sub, search
from urllib.parse import quote, urlsplit, urlunsplit
from urllib.request import Request, urlopen
from gzip import decompress
from worker import WorkerExit, UserWorker
from traceback import print_exc
from http.cookies import SimpleCookie

from .safeprint import safeprint
from .error import *
from .io import content_write, is_file
from .config import setting

import pprint, traceback, os

default_header = {
	"User-Agent": "Mozilla/5.0 (Windows NT 6.1; WOW64; rv:34.0) Gecko/20100101 Firefox/34.0",
	"Accept-Language": "zh-tw,zh;q=0.8,en-us;q=0.5,en;q=0.3",
	"Accept-Encoding": "gzip, deflate"
}

class Mission(UserWorker):
	"""Create Mission object. Contains information of the mission."""

	def __init__(self, title=None, url=None, episodes=None, state="INIT"):
		"""Construct."""
		from .mods import get_module

		super().__init__()

		self.title = title
		self.url = url
		self.episodes = episodes
		self.state = state
		self.module = get_module(url)
		if not self.module:
			raise ModuleError("Get module failed!")

	def set(self, key, value):
		"""Set new attribute."""

		if not hasattr(self, key):
			return

		setattr(self, key, value)
		self.bubble("MISSION_PROPERTY_CHANGED", self)

class Episode:
	"""Create Episode object. Contains information of an episode."""

	def __init__(self, title=None, url=None, current_url=None, current_page=0, skip=False, complete=False):
		"""Construct."""
		self.title = title
		self.url = url
		self.current_url = current_url
		self.current_page = current_page
		self.skip = skip
		self.complete = complete

def format_escape(s):
	"""Escape {} to {{}}"""
	return sub("([{}])", r"\1\1", s)

def getext(byte):
	"""Return extension by testing the byte stream.

	imghdr issue: http://bugs.python.org/issue16512
	"""
	r = what("", byte)
	if r:
		if r.lower() == "jpeg":
			return "jpg"
		return r.lower()

	h = byte
	if h[:2] == b"\xff\xd8":
		return "jpg"

	if h[:3] == b"CWS" or h[:3] == b"FWS":
		return "swf"

	if h[:4] == b"8BPS":
		return "psd"

	if h[:7] == b"Rar!\x1a\x07\x00":
		return "rar"

	if h[:4] == b"PK\x03\x04":
		return "zip"

	if h[:4] == b"\x1A\x45\xDF\xA3":
		return "mkv"

	return None

def safefilepath(s):
	"""Return a safe directory name."""
	return sub("[/\\\?\|<>:\"\*]","_",s).strip()

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
				"header value must be str!\n" + pprint.pformat(header)
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

	response = urlopen(request, timeout=20)

	jar.load(response.getheader("Set-Cookie", ""))
	if cookie is not None:
		for key, c in jar.items():
			cookie[key] = c.value

	b = response.read()

	# decompress gziped data
	if response.getheader("Content-Encoding") == "gzip":
		b = decompress(b)

	if raw:
		content = b

	else:
		# find html defined encoding
		s = b.decode("utf-8", "replace")
		match = search(r"charset=[\"']?([^\"'>]+)", s)
		if match:
			s = b.decode(match.group(1), "replace")
		content = s

	if errorlog or setting.getboolean("errorlog"):
		log_object = (
			url,
			request.header_items(),
			response.getheaders()
		)
		if not errorlog:
			errorlog = ""
		from pprint import pformat
		content_write("~/comiccrawler/grabber.log", pformat(log_object) + "\n\n", append=True)

	return content

def grabhtml(*args, **kwargs):
	"""Get html source of given url. Return String."""
	kwargs["raw"] = False
	return grabber(*args, **kwargs)

def grabimg(*args, **kwargs):
	"""Return byte array."""
	kwargs["raw"] = True
	return grabber(*args, **kwargs)

def download(mission, savepath, thread=None):
	"""Download mission to savepath."""

	# warning there is a deadlock,
	# never do mission.lock.acquire in callback...
	safeprint("Start downloading " + mission.title)
	mission.set("state", "DOWNLOADING")
	try:
		crawl(mission, savepath, thread)
	except WorkerExit:
		mission.set("state", "PAUSE")
		raise
	except Exception:
		mission.set("state", "ERROR")
		thread.bubble("DOWNLOAD_ERROR", mission)
		raise
	except PauseDownloadError:
		mission.set("state", "ERROR")
		thread.bubble("DOWNLOAD_INVALID", mission)
	else:
		mission.set("state", "FINISHED")
		thread.bubble("DOWNLOAD_FINISHED", mission)

def crawl(mission, savepath, thread):
	"""Crawl each episode."""
	episodes = mission.episodes
	module = mission.module

	safeprint("total {} episode.".format(len(episodes)))

	for ep in episodes:
		if ep.skip or ep.complete:
			continue

		if getattr(module, "noepfolder", False):
			efd = join(savepath, safefilepath(mission.title))
			fexp = format_escape(safefilepath(ep.title)) + "_{:03}"
		else:
			efd = join(savepath, safefilepath(mission.title),
					safefilepath(ep.title))
			fexp = "{:03}"

		safeprint("Downloading ep {}".format(ep.title))

		try:
			crawlpage(ep, module, efd, fexp, thread)

		except LastPageError:
			safeprint("Episode download complete!")
			ep.complete = True
			thread.bubble("DOWNLOAD_EP_COMPLETE", (mission, ep))

		except SkipEpisodeError:
			safeprint("Something bad happened, skip the episode.")
			ep.skip = True
	else:
		safeprint("Mission complete!")

class Crawler:
	"""Create Crawler object. Contains img url, next page url."""

	def __init__(self, ep, downloader, savepath, fexp, thread):
		"""Construct."""
		self.ep = ep
		self.downloader = downloader
		self.savepath = savepath
		self.fexp = fexp
		self.thread = thread
		self.exist_pages = None

	def page_exists(self):
		"""Check if current page exists in savepath."""
		if self.exist_pages is None:
			self.exist_pages = set()
			if os.path.isdir(self.savepath):
				for file in  os.listdir(self.savepath):
					if os.path.isfile(os.path.join(self.savepath, file)):
						self.exist_pages.add(os.path.splitext(file)[0])
		return self.get_filename() in self.exist_pages

	def get_filename(self):
		"""Get current page file name."""
		return self.fexp.format(self.ep.current_page)

	def download_image(self):
		"""Download image to savepath."""
		image = self.thread.sync(
			grabimg,
			self.get_img(),
			self.get_header(),
			referer=self.ep.current_url
		)
		# check image type
		ext = getext(image)
		if not ext:
			raise TypeError("Invalid image type.")
		# everything is ok, save image
		full_filename = join(
			self.savepath,
			"{}.{}".format(self.get_filename(), ext)
		)
		content_write(full_filename, image)

	def iter_next(self):
		"""Iter to next page."""
		nextpageurl = self.get_nextpage()
		if not nextpageurl:
			raise LastPageError

		self.ep.current_url = nextpageurl
		self.ep.current_page += 1

	def rest(self):
		"""Rest some time."""
		self.thread.wait(self.get_rest())

	def get_img(self):
		"""Override me. Return img url. It should cahe each page."""
		pass

	def get_nextpage(self):
		"""Override me. Return next page url."""
		pass

	def flush(self):
		"""Override me. Cleanup url cache."""
		pass

	def get_header(self):
		"""Return downloader header."""
		return getattr(self.downloader, "header", None)

	def get_rest(self):
		"""Return downloader rest."""
		return getattr(self.downloader, "rest", 0)

	def get_cookie(self):
		"""Return downloader cookie."""
		return getattr(self.downloader, "cookie", None)

	def handle_error(self, error):
		"""Send error to error handler."""
		handler = getattr(self.downloader, "errorhandler", None)
		if not handler:
			return

		try:
			handler(error, self.ep)

		except Exception as er:
			print("[Crawler] Failed to handle error: {}".format(er))

class PerPageCrawler(Crawler):
	"""Iter over per pages."""

	def __init__(self, *args):
		"""Extend. Add cache."""
		super().__init__(*args)
		self.cache = {}
		self.cache_img = {}

	def get_html(self):
		"""Return html."""
		url = self.ep.current_url
		if not url:
			raise LastPageError
		if url not in self.cache:
			self.cache[url] = self.thread.sync(
				grabhtml,
				self.ep.current_url,
				self.get_header(),
				cookie=self.get_cookie()
			)
		return self.cache[url]

	def get_img(self):
		"""Override."""
		page = self.ep.current_page
		if page not in self.cache_img:
			self.cache_img[page] = self.thread.sync(
				self.downloader.getimgurl,
				self.get_html(),
				self.ep.current_url,
				self.ep.current_page,
			)
		return self.cache_img[page]

	def get_nextpage(self):
		"""Override."""
		return self.thread.sync(
			self.downloader.getnextpageurl,
			self.get_html(),
			self.ep.current_url,
			self.ep.current_page,
		)

	def flush(self):
		"""Override."""
		if self.cache:
			self.cache = {}
		if self.cache_img:
			self.cache_img = {}

class AllPageCrawler(Crawler):
	"""Get all info in first page."""

	def __init__(self, *args):
		"""Extend."""
		super().__init__(*args)
		self.imgurls = None
		self.create_imgurls()

	def create_imgurls(self):
		"""Create imgurls."""
		def process():
			html = self.thread.sync(
				grabhtml,
				self.ep.url,
				self.get_header(),
				cookie=self.get_cookie()
			)

			imgurls = self.thread.sync(
				self.downloader.getimgurls,
				html,
				self.ep.url
			)

			if not imgurls:
				raise Exception("imgurls is empty")

			self.imgurls = imgurls
			raise ExitErrorLoop

		def handle_error(er):
			self.handle_error(er)
			self.thread.wait(5)

		error_loop(process, handle_error)

	def get_imgurls(self):
		"""Try to get imgurls."""
		return self.imgurls

	def get_img(self):
		"""Return img url."""
		urls = self.get_imgurls()
		if self.ep.current_page > len(urls):
			raise LastPageError
		return urls[self.ep.current_page - 1]

	def get_nextpage(self):
		"""Return next page. Always use first page."""
		urls = self.get_imgurls()
		if self.ep.current_page < len(urls):
			return self.ep.url

def crawlpage(ep, downloader, savepath, fexp, thread):
	"""Crawl all pages of an episode.

	To complete current episode, raise LastPageError.
	To skip current episode, raise SkipEpisodeError.
	To stop downloading (fatal error), raise PauseDownloadError.
	"""
	if not ep.current_page:
		ep.current_page = 1

	if not ep.current_url:
		ep.current_url = ep.url

	if hasattr(downloader, "getimgurls"):
		crawler = AllPageCrawler(ep, downloader, savepath, fexp, thread)
	else:
		crawler = PerPageCrawler(ep, downloader, savepath, fexp, thread)

	def download():
		if not crawler.page_exists():
			safeprint("Downloading {} page {}: {}\n".format(
					ep.title, ep.current_page, crawler.get_img()))
			crawler.download_image()
			crawler.iter_next()
			crawler.rest()

		else:
			safeprint("page {} already exist".format(
					ep.current_page))
			crawler.iter_next()

	def download_error(er):
		crawler.handle_error(er)
		crawler.flush()
		thread.wait(5)

	error_loop(download, download_error)

def error_loop(process, handle_error=None, limit=10):
	"""Loop process until error. Has handle error limit."""
	errorcount = 0
	while True:
		try:
			process()
		except Exception as er:
			print("[error_loop] Process error: ", er)
			errorcount += 1
			if errorcount >= limit:
				raise Exception("Exceed error loop limit!")
			if handle_error:
				try:
					handle_error(er)
				except Exception as er:
					print("[error_loop] Error handler error: ", er)
		except ExitErrorLoop:
			break
		else:
			errorcount = 0

def analyze(mission, thread=None):
	"""Analyze mission."""
	try:
		analyze_info(mission, mission.module, thread)

	except WorkerExit:
		mission.set("state", "ERROR")
		raise

	except Exception as er:
		mission.set("state", "ERROR")
		print_exc()
		thread.bubble("ANALYZE_FAILED", (mission, er))

	except PauseDownloadError:
		mission.set("state", "ERROR")
		thread.bubble("ANALYZE_INVALID", mission)

	else:
		thread.bubble("ANALYZE_FINISHED", mission)

def remove_duplicate_episode(mission):
	"""Remove duplicate episodes."""
	s = set()
	cleanList = []
	for ep in mission.episodes:
		if ep.url not in s:
			s.add(ep.url)
			cleanList.append(ep)
	mission.episodes = cleanList

def analyze_info(mission, downloader, thread):
	"""Analyze mission."""
	safeprint("Start analyzing {}".format(mission.url))

	mission.set("state", "ANALYZING")

	header = getattr(downloader, "header", None)
	cookie = getattr(downloader, "cookie", None)

	html = thread.sync(grabhtml, mission.url, header, cookie=cookie)

	if not mission.title:
		mission.title = downloader.gettitle(html, mission.url)

	episodes = thread.sync(downloader.getepisodelist, html, mission.url)

	if not episodes:
		raise Exception("Episode list is empty")

	# Check if re-analyze
	if mission.episodes:
		# Insert new episodes
		old_eps = set([ep.url for ep in mission.episodes])
		for ep in episodes:
			if ep.url not in old_eps:
				mission.episodes.append(ep)

		# Check update
		for ep in mission.episodes:
			if not ep.skip and not ep.complete:
				mission.set("state", "UPDATE")
				break
		else:
			mission.set("state", "FINISHED")

	else:
		mission.episodes = episodes
		mission.set("state", "ANALYZED")

	# remove duplicate
	remove_duplicate_episode(mission)

	safeprint("Analyzing success!")
