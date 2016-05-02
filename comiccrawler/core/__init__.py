#! python3

import traceback
import imghdr
import re
import hashlib
import json

from worker import sleep, WorkerExit
from os import extsep
from os.path import join as path_join, split as path_split, splitext

from ..safeprint import print
from ..error import *
from ..io import content_write, content_read, path_each
from ..config import setting
from ..channel import download_ch, mission_ch

from .grabber import grabhtml, grabimg

class Mission:
	"""Create Mission object. Contains information of the mission."""

	def __init__(self, title=None, url=None, episodes=None, state="INIT"):
		"""Construct."""
		from ..mods import get_module

		super().__init__()

		self.title = title
		self.url = url
		self.episodes = episodes
		self.state = state
		self.module = get_module(url)
		if not self.module:
			raise ModuleError("Get module failed!")
			
class MissionProxy:
	"""Publish MISSION_PROPERTY_CHANGED event when property changed"""
	def __init__(self, mission):
		self.__dict__["mission"] = mission

	def __getattr__(self, name):
		return getattr(self.mission, name)

	def __setattr__(self, name, value):
		setattr(self.mission, name, value)
		mission_ch.pub("MISSION_PROPERTY_CHANGED", self)

	def tojson(self):
		json = vars(self.mission).copy()
		del json["module"]
		return json
		
def create_mission(url):
	return MissionProxy(Mission(url=url))

class Episode:
	"""Create Episode object. Contains information of an episode."""

	def __init__(self, title=None, url=None, current_url=None, current_page=0, skip=False, complete=False, total=0, image=None):
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
		self.image = image

def format_escape(s):
	"""Escape {} to {{}}"""
	return re.sub("([{}])", r"\1\1", s)
	
VALID_FILE_TYPES = (
	# images
	".jpg", ".jpeg", ".gif", ".png", ".svg", ".psd",
	# zips
	".zip", ".rar",
	# videos
	".mp4", ".mkv", ".swf"
)

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
		
	# FIXME: maybe we should see http header content type for file extension
	# http://www.garykessler.net/library/file_sigs.html
	if h[4:8] == b"ftyp":
		return "mp4"

	return None
	
def safefilepath(s):
	"""Return a safe directory name."""
	return re.sub("[/\\\?\|<>:\"\*]","_",s).strip()

def download(mission, savepath):
	"""Download mission to savepath."""

	# warning there is a deadlock,
	# never do mission.lock.acquire in callback...
	print("Start downloading " + mission.title)
	mission.state = "DOWNLOADING"
	try:
		crawl(mission, savepath)

		# Check if mission is complete
		for ep in mission.episodes:
			if not ep.complete and not ep.skip:
				raise Exception("Mission is not completed")

	except WorkerExit:
		mission.state = "PAUSE"
		download_ch.pub('DOWNLOAD_PAUSE', mission)
		raise

	except PauseDownloadError as err:
		mission.state = "ERROR"
		download_ch.pub('DOWNLOAD_INVALID', (err, mission))

	except Exception as err:
		mission.state = "ERROR"
		download_ch.pub('DOWNLOAD_ERROR', (err, mission))
		raise

	else:
		mission.state = "FINISHED"
		download_ch.pub("DOWNLOAD_FINISHED", mission)	
	
def crawl(mission, savepath):
	"""Crawl each episode."""
	episodes = mission.episodes
	module = mission.module

	print("total {} episode.".format(len(episodes)))

	for ep in episodes:
		if ep.skip or ep.complete:
			continue

		if getattr(module, "noepfolder", False):
			efd = path_join(savepath, safefilepath(mission.title))
			fexp = format_escape(safefilepath(ep.title)) + "_{:03}"
		else:
			efd = path_join(savepath, safefilepath(mission.title),
					safefilepath(ep.title))
			fexp = "{:03}"

		print("Downloading ep {}".format(ep.title))
		
		try:
			crawler = Crawler(mission, ep, module, efd, fexp)
			crawlpage(crawler)

		except LastPageError:
			print("Episode download complete!")
			ep.complete = True
			download_ch.pub("DOWNLOAD_EP_COMPLETE", (mission, ep))

		except SkipEpisodeError as err:
			print("Something bad happened, skip the episode.")
			if err.always:
				ep.skip = True

def get_checksum(b):
	return hashlib.md5(b).hexdigest()

def get_file_checksum(file):
	return get_checksum(content_read(file, raw=True))

def extract_filename(file):
	dir, fn = path_split(file)
	fn, ext = splitext(fn)
	return fn
	
class Crawler:
	"""Create Crawler object. Contains img url, next page url."""
	def __init__(self, mission, ep, downloader, savepath, fexp):
		"""Construct."""
		self.mission = mission
		self.ep = ep
		self.savepath = savepath
		self.downloader = downloader
		self.fexp = fexp
		self.exist_pages = None
		self.checksums = None
		self.is_init = False
		self.html = None
		self.image = None
		self.image_bin = None
		self.image_ext = None
		
	def init(self):
		if not self.ep.current_url:
			self.ep.current_url = self.ep.url
		if not self.ep.current_page:
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
			
		is_init = True
			
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
		self.image_ext, self.image_bin = grabimg(
			self.image,
			self.get_header(),
			referer=self.ep.current_url
		)

	def get_full_filename(self):
		"""Generate full filename including extension"""
		
		# try to get proper ext for image
		ext = getext(self.image_bin)
		if ext:
			self.image_ext = extsep + ext
			
		if not self.image_ext:
			raise Exception("Can't determine file type.")
			
		if self.image_ext not in VALID_FILE_TYPES:
			raise Exception("Bad file type: " + self.image_ext)
			
		return path_join(
			self.savepath,
			self.get_filename() + self.image_ext
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
			self.image = self.image()
		
	def rest(self):
		"""Rest some time."""
		sleep(getattr(self.downloader, "rest", 0))
		
	def get_next_page(self):
		if hasattr(self.downloader, "get_next_page"):
			return self.downloader.get_next_page(
				self.html,
				self.ep.current_url
			)
		
	def get_html(self):
		if self.ep.image:
			return
		self.html = grabhtml(
			self.ep.current_url,
			self.get_header(),
			cookie=self.get_cookie()
		)
		
	def get_images(self):
		"""Get images"""
		if self.ep.image:
			images = self.ep.image
		else:
			images = self.downloader.get_images(
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

			
def crawlpage(crawler):
	"""Crawl all pages of an episode.

	To complete current episode, raise LastPageError.
	To skip current episode, raise SkipEpisodeError.
	To stop downloading (fatal error), raise PauseDownloadError.
	"""
	
	def download():
		if not crawler.is_init:
			crawler.init()
	
		if not crawler.image:
			crawler.next_page()
			return
			
		if crawler.page_exists():
			print("page {} already exist".format(crawler.ep.total + 1))
			crawler.next_image()
			return
			
		crawler.resolve_image()
		print("Downloading {} page {}: {}\n".format(
			crawler.ep.title, crawler.ep.total + 1, crawler.image))
		crawler.download_image()
		crawler.save_image()
		mission_ch.pub("MISSION_PROPERTY_CHANGED", crawler.mission)
		crawler.rest()
		crawler.next_image()

	def download_error(er):
		crawler.handle_error(er)
		sleep(5)

	error_loop(download, download_error)

def error_loop(process, handle_error=None, limit=10):
	"""Loop process until error. Has handle error limit."""
	errorcount = 0
	while True:
		try:
			process()
		except Exception as er:
			traceback.print_exc()
			errorcount += 1
			if errorcount >= limit:
				raise SkipEpisodeError(always=False)
			if handle_error:
				handle_error(er)
		except ExitErrorLoop:
			break
		else:
			errorcount = 0

def analyze(mission):
	"""Analyze mission."""
	try:
		analyze_info(mission, mission.module)

	except WorkerExit:
		mission.state = "ERROR"
		raise

	except Exception as err:
		mission.state = "ERROR"
		traceback.print_exc()
		download_ch.pub("ANALYZE_FAILED", (err, mission))

	except PauseDownloadError as err:
		mission.state = "ERROR"
		download_ch.pub("ANALYZE_INVALID", (err, mission))

	else:
		download_ch.pub("ANALYZE_FINISHED", mission)

def remove_duplicate_episode(mission):
	"""Remove duplicate episodes."""
	s = set()
	cleanList = []
	for ep in mission.episodes:
		if ep.url not in s:
			s.add(ep.url)
			cleanList.append(ep)
	mission.episodes = cleanList

def analyze_info(mission, downloader):
	"""Analyze mission."""
	print("Start analyzing {}".format(mission.url))

	mission.state = "ANALYZING"

	header = getattr(downloader, "header", None)
	cookie = getattr(downloader, "cookie", None)

	html = grabhtml(mission.url, header, cookie=cookie)

	if not mission.title:
		mission.title = downloader.get_title(html, mission.url)

	if mission.episodes:
		old_urls = set(map(lambda e: e.url, mission.episodes))
	else:
		old_urls = set()
		
	url = mission.url
	episodes = []
	while True:
		eps = downloader.get_episodes(html, url)
		episodes = list(eps) + episodes
		if any(ep.url in old_urls for ep in eps):
			break
		if not hasattr(downloader, "get_next_page"):
			break
		if len(episodes) and episodes[0].url == mission.url:
			break
		next_url = downloader.get_next_page(html, url)
		if not next_url:
			break
		url = next_url
		print('Analyzing {}...'.format(url))
		html = grabhtml(url, header, cookie=cookie)

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
		if not episodes:
			raise Exception("Episode list is empty")

		mission.episodes = episodes
		mission.state = "ANALYZED"

	# remove duplicate
	remove_duplicate_episode(mission)

	print("Analyzing success!")
