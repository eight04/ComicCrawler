#! python3

from urllib.parse import quote, urlsplit, urlunsplit
from urllib.request import Request, urlopen
from urllib.error import HTTPError

from http.cookies import SimpleCookie

from .safeprint import safeprint
from .error import *
from .io import content_write, content_read, path_each
from .config import setting

import pprint, traceback, os, imghdr, re, time, hashlib, gzip, worker

default_header = {
	"User-Agent": "Mozilla/5.0 (Windows NT 6.1; WOW64; rv:34.0) Gecko/20100101 Firefox/34.0",
	"Accept-Language": "zh-tw,zh;q=0.8,en-us;q=0.5,en;q=0.3",
	"Accept-Encoding": "gzip, deflate"
}

class Mission:
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

class Episode:
	"""Create Episode object. Contains information of an episode."""

	def __init__(self, title=None, url=None, current_url=None, current_page=0, skip=False, complete=False, total=0):
		"""Construct."""
		self.title = title
		self.url = url
		self.current_url = current_url
		# position of images on current page
		self.current_page = current_page
		self.skip = skip
		self.complete = complete
		# total number of images in this episode
		self.total = total

def format_escape(s):
	"""Escape {} to {{}}"""
	return re.sub("([{}])", r"\1\1", s)

def getext(byte):
	"""Return extension by testing the byte stream.

	imghdr issue: http://bugs.python.org/issue16512
	"""
	r = imghdr.what("", byte)
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
	return re.sub("[/\\\?\|<>:\"\*]","_",s).strip()

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
				time.sleep(retry)
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
	mission.state = "DOWNLOADING"
	try:
		crawl(mission, savepath, thread)

		# Check if mission is complete
		for ep in mission.episodes:
			if not ep.complete and not ep.skip:
				raise Exception("Mission is not completed")

	except worker.WorkerExit:
		mission.state = "PAUSE"
		raise

	except Exception:
		mission.state = "ERROR"
		thread.bubble("DOWNLOAD_ERROR", mission)
		raise

	except PauseDownloadError:
		mission.state = "ERROR"
		thread.bubble("DOWNLOAD_INVALID", mission)

	else:
		mission.state = "FINISHED"
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
			efd = os.path.join(savepath, safefilepath(mission.title))
			fexp = format_escape(safefilepath(ep.title)) + "_{:03}"
		else:
			efd = os.path.join(savepath, safefilepath(mission.title),
					safefilepath(ep.title))
			fexp = "{:03}"

		safeprint("Downloading ep {}".format(ep.title))

		try:
			crawlpage(ep, module, efd, fexp, thread, mission.save)

		except LastPageError:
			safeprint("Episode download complete!")
			ep.complete = True
			thread.bubble("DOWNLOAD_EP_COMPLETE", (mission, ep))

		except SkipEpisodeError as err:
			safeprint("Something bad happened, skip the episode.")
			if err.always:
				ep.skip = True

def get_checksum(b):
	return hashlib.md5(b).hexdigest()

def get_file_checksum(file):
	return get_checksum(content_read(file, raw=True))

def extract_filename(file):
	dir, fn = os.path.split(file)
	fn, ext = os.path.splitext(fn)
	return fn
	
class Crawler:
	"""Create Crawler object. Contains img url, next page url."""

	def __init__(self, ep, downloader, savepath, fexp, thread):
		"""Construct."""
		self.ep = ep
		self.savepath = savepath
		self.downloader = downloader
		self.fexp = fexp
		self.thread = thread
		self.exist_pages = None
		
		if not self.ep.current_url:
			self.ep.current_url = self.ep.url
			self.ep.current_page = 1
			
		self.get_html()
		self.get_images()
		
		# skip some images
		try:
			for i in range(0, self.ep.current_page - 1):
				next(self.images)
			self.image = next(self.images)
		except StopIteration:
			# cannot find the page?
			self.image = None
			
	def page_exists(self):
		"""Check if current page exists in savepath."""
		if self.exist_pages is None:
			self.exist_pages = set()
			path_each(
				self.savepath,
				lambda file: self.exist_pages.add(extract_filename(file))
			)
		return self.get_filename() in self.exist_pages

	def get_filename(self):
		"""Get current page file name."""
		return self.fexp.format(self.ep.total + 1)

	def download_image(self):
		"""Download image"""
		self.image_bin = self.thread.sync(
			grabimg,
			self.image,
			self.get_header(),
			referer=self.ep.current_url
		)

	def get_full_filename(self):
		"""Generate full filename including extension"""
		ext = getext(self.image_bin)
		if not ext:
			raise TypeError("Invalid image type.")
		return os.path.join(
			self.savepath,
			self.get_filename() + os.extsep + ext
		)

	def save_image(self):
		"""Write image to save path"""
		if getattr(self.downloader, "circular", False):
			if not self.checksums:
				self.checksums = set()
				path_each(
					self.savepath,
					lambda file: self.checksums.add(get_file_checksum(file))
				)

			checksum = get_checksum(self.image_bin)
			if checksum in self.checksums:
				raise LastPageError
			else:
				self.checksums.add(checksum)

		content_write(self.get_full_filename(), self.image_bin)

	def next_page(self):
		"""Iter to next page."""
		next_page = self.get_next_page()
		if not next_page:
			raise LastPageError
			
		self.ep.current_url = next_page
		self.ep.current_page = 1
		
		self.get_html()
		self.get_images()
		
		try:
			self.image = next(self.images)
		except StopIteration:
			self.image = None

	def next_image(self):
		self.ep.current_page += 1
		self.ep.total += 1
		try:
			self.image = next(self.images)
		except StopIteration:
			self.image = None
	
	def resolve_image(self):
		if callable(self.image):
			self.image = self.thread.sync(self.image)		
		
	def rest(self):
		"""Rest some time."""
		self.thread.wait(getattr(self.downloader, "rest", 0))
		
	def get_next_page(self):
		if hasattr(self.downloader, "get_next_page"):
			return self.thread.sync(
				self.downloader.get_next_page,
				self.html,
				self.ep.current_url
			)
		
	def get_html(self):
		self.html = self.thread.sync(
			grabhtml,
			self.ep.current_url,
			self.get_header(),
			cookie=self.get_cookie()
		)
		
	def get_images(self):
		"""Get images"""
		images = self.thread.sync(
			self.downloader.get_images,
			self.html, 
			self.ep.current_url
		)
		if isinstance(images, str):
			images = [images]
		self.images = iter(images)
		
	def get_header(self):
		"""Return downloader header."""
		return getattr(self.downloader, "header", None)

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

			
def crawlpage(ep, downloader, savepath, fexp, thread, page_done):
	"""Crawl all pages of an episode.

	To complete current episode, raise LastPageError.
	To skip current episode, raise SkipEpisodeError.
	To stop downloading (fatal error), raise PauseDownloadError.
	"""
	crawler = Crawler(ep, downloader, savepath, fexp, thread)
	
	def download():
		if not crawler.image:
			crawler.next_page()
			return
			
		if crawler.page_exists():
			safeprint("page {} already exist".format(ep.total + 1))
			crawler.next_image()
			return
			
		crawler.resolve_image()
		safeprint("Downloading {} page {}: {}\n".format(
			ep.title, ep.total + 1, crawler.image))
		crawler.download_image()
		crawler.save_image()
		page_done()
		crawler.rest()
		crawler.next_image()

	def download_error(er):
		crawler.handle_error(er)
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
				raise SkipEpisodeError(always=False)
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

	except worker.WorkerExit:
		mission.state = "ERROR"
		raise

	except Exception as er:
		mission.state = "ERROR"
		traceback.print_exc()
		thread.bubble("ANALYZE_FAILED", (mission, er))

	except PauseDownloadError:
		mission.state = "ERROR"
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

	mission.state = "ANALYZING"

	header = getattr(downloader, "header", None)
	cookie = getattr(downloader, "cookie", None)

	html = thread.sync(grabhtml, mission.url, header, cookie=cookie)

	if not mission.title:
		mission.title = downloader.get_title(html, mission.url)

	if mission.episodes:
		last_ep = mission.episodes[-1]
	else:
		last_ep = None
		
	url = mission.url
	episodes = []
	while True:
		eps = thread.sync(downloader.get_episodes, html, url)
		episodes = list(eps) + episodes
		if last_ep and any(ep.url == last_ep.url for ep in eps):
			break
		if not hasattr(downloader, "get_next_page"):
			break
		next_url = thread.sync(downloader.get_next_page, html, url)
		if not next_url:
			break
		url = next_url
		html = thread.sync(grabhtml, url, header, cookie=cookie)

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
				mission.state = "UPDATE"
				break
		else:
			mission.state = "FINISHED"

	else:
		mission.episodes = episodes
		mission.state = "ANALYZED"

	# remove duplicate
	remove_duplicate_episode(mission)

	safeprint("Analyzing success!")
