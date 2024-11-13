import hashlib
import json
import traceback
from pathlib import Path
from urllib.parse import urlparse

from worker import WorkerExit, sleep

from .save_path import SavePath
from .module_grabber import ModuleGrabber
from .image import Image
from .error import LastPageError, PauseDownloadError, SkipEpisodeError, is_http, SkipPageError, ComicCrawlerError

from .io import content_read, content_write
from .util import url_extract_filename
from .channel import download_ch, mission_ch
from .safeprint import print
from .logger import debug_log

VALID_FILE_TYPES = (
	# images
	".jpg", ".jpeg", ".gif", ".png", ".svg", ".psd", ".webp", ".bmp", ".clip",
	# zips
	".zip", ".rar",
	# videos
	".mp4", ".m4v", ".mkv", ".swf", ".webm", ".mov", ".wmv",
	# audio
	".mp3", ".aac", ".flac", ".wav",
	# json
	".json", ".txt"
)

class Crawler:
	"""Create Crawler object. Contains img url, next page url."""
	def __init__(self, mission, ep, savepath):
		"""Construct."""
		self.mission = mission
		self.ep = ep
		self.savepath = SavePath(savepath, mission, ep)
		self.mod = mission.module
		self.downloader = ModuleGrabber(mission.module)
		self.checksums = None
		self.is_init = False
		self.html = None
		self.image = None
		self.images = None
		self.image_bin = None
		self.image_ext = None
		self.tempfile = None
		self.tempfile_complete = False
		
	def init(self):
		if not self.ep.current_url:
			self.ep.current_url = self.ep.url
		if not self.ep.current_page:
			self.ep.current_page = 1
			
		self.init_images(self.ep.current_page - 1)
			
		self.is_init = True
		
	def init_images(self, skip_pages=0):
		"""Grab html, images and move cursor to correct image by skip_pages"""
		self.get_html()
		self.get_images()
		
		try:
			# skip some images
			for _ in range(0, skip_pages):
				next(self.images)
			# get current image
			self.image = Image.create(next(self.images))
		except StopIteration:
			self.image = None
			
	def get_filename(self):
		if self.mission.module.config.getboolean("originalfilename"):
			return self.image.filename
		return self.ep.total + 1
		
	def page_exists(self):
		return self.savepath.exists(self.get_filename())
			
	def download_image(self):
		"""Download image"""
		if not self.image:
			raise ValueError("No image to download")

		if self.image.url:
			self.tempfile = self.savepath.full_fn(self.get_filename(), ".part")

			def on_opened(response):
				if response.history:
					self.handle_redirect(response)
				if after_request := getattr(self.mod, "after_request", None):
					after_request(self, response)

			result = self.downloader.img(
				self.image.url,
				referer=None if getattr(self.mod, "no_referer", False) else self.ep.current_url,
				# FIXME: doesn't work with dynamic filename if redirected
				tempfile=self.tempfile,
				on_opened=on_opened
			)
			self.tempfile_complete = True
				
			# redirected and url changed
			if result.response.history and not self.image.static_filename:
				self.image.filename = url_extract_filename(result.response.url)

			bin = result.bin
			ext = result.ext
		else:
			bin = json.dumps(self.image.data, indent="\t").encode("utf-8")
			ext = ".json"
			
		if not ext:
			raise ValueError("Bad file type, the file extension is undefined")
			
		if ext not in VALID_FILE_TYPES:
			raise ValueError("Bad file type: " + ext)
			
		self.image_bin = bin
		self.image_ext = ext
		
	def handle_redirect(self, response):
		"""FIXME: should we merge this into handle_image?"""
		if hasattr(self.mod, "redirecthandler"):
			self.mod.redirecthandler(response, self)
			
	def handle_image(self):
		"""Post processing"""
		if hasattr(self.mod, "imagehandler"):
			if not self.image_bin and self.tempfile_complete:
				self.image_bin = content_read(self.tempfile, raw=True)
			self.image_ext, self.image_bin = self.mod.imagehandler(
				self.image_ext, self.image_bin)

	def save_image(self):
		"""Write image to save path"""
		if getattr(self.mod, "circular", False):
			if not self.checksums:
				self.checksums = set()
				for file in Path(self.savepath.parent()).iterdir():
					if not file.is_file():
						continue
					if file.suffix not in VALID_FILE_TYPES:
						continue
					self.checksums.add(get_file_checksum(file))

			if not self.image_bin and self.tempfile_complete:
				checksum = get_file_checksum(self.tempfile)
			else:
				checksum = get_checksum(self.image_bin)

			if checksum in self.checksums:
				if self.tempfile:
					Path(self.tempfile).unlink(True)
				raise LastPageError
			self.checksums.add(checksum)

		if not self.image_ext:
			raise ValueError("No image extension")
				
		try:
			output = self.savepath.full_fn(self.get_filename(), self.image_ext)
			if self.tempfile:
				Path(self.tempfile).rename(output)
			else:
				content_write(output, self.image_bin)
		except OSError as err:
			traceback.print_exc()
			raise PauseDownloadError("Failed to write file!") from err

	def next_page(self):
		"""Iter to next page."""
		next_page = self.get_next_page()
		if not next_page:
			raise LastPageError
			
		self.ep.current_url = next_page
		self.ep.current_page = 1
		
		self.image_bin = None
		self.image_ext = None
		self.tempfile = None
		self.tempfile_complete = False

		self.init_images()

	def next_image(self):
		self.ep.current_page += 1
		self.ep.total += 1
		try:
			self.image = Image.create(next(self.images))
		except StopIteration:
			self.image = None
			
	def resolve_image(self):
		self.image.resolve()
		
	def rest(self):
		"""Rest some time."""
		sleep(getattr(self.mod, "rest", 0))
		
	def get_next_page(self):
		# self.html is not a str if self.ep.image is not None
		if not isinstance(self.html, str):
			return
		if hasattr(self.mod, "get_next_image_page"):
			return self.mod.get_next_image_page(self.html, self.ep.current_url)
		if hasattr(self.mod, "get_next_page"):
			return self.mod.get_next_page(
				self.html,
				self.ep.current_url
			)
		
	def get_html(self):
		if self.ep.image:
			self.html = True
		else:
			r = urlparse(self.mission.url)
			self.html = self.downloader.html(self.ep.current_url, header={
				"Referer": self.mission.url,
				"Origin": f"{r.scheme}://{r.netloc}"
				})
		
	def get_images(self):
		"""Get images"""
		skip_page = False
		if self.ep.image:
			images = self.ep.image
		else:
			try:
				images = self.mod.get_images(
					self.html,
					self.ep.current_url
				)
			except SkipPageError:
				images = []
				skip_page = True
		if isinstance(images, str):
			images = [images]
		if not images and not skip_page:
			raise ValueError("get_images returns an empty array")
		try:
			self.images = iter(images)
		except TypeError:
			self.images = iter([images])
		
	def handle_error(self, error):
		"""Send error to error handler."""
		handler = getattr(self.mod, "errorhandler", None)
		if not handler:
			return

		try:
			handler(error, self)

		except Exception as err: # pylint: disable=broad-except
			print("[Crawler] Failed to handle error: {}".format(err))
			traceback.print_exc()
			
def get_checksum(b):
	return hashlib.md5(b).hexdigest() # nosec

def get_file_checksum(file):
	with Path(file).open("rb") as f:
		# NOTE: this only works with python 3.11+
		digest = hashlib.file_digest(f, "md5") # pylint: disable=no-member
		return digest.hexdigest()

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
				raise ComicCrawlerError("Mission is not completed")

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
	
	print("total {} episode.".format(len(mission.episodes)))

	for ep in mission.episodes:
		if ep.skip or ep.complete:
			continue

		print("Downloading ep {}".format(ep.title))
		
		try:
			crawler = Crawler(mission, ep, savepath)
			crawlpage(crawler)

		except LastPageError:
			print("Episode download complete!")
			ep.complete = True
			download_ch.pub("DOWNLOAD_EP_COMPLETE", (mission, ep))

		except SkipEpisodeError as err:
			print("Something bad happened, skip the episode.")
			if err.always:
				ep.skip = True

def crawlpage(crawler):
	"""Crawl all pages of an episode.

	To complete current episode, raise LastPageError.
	To skip current episode, raise SkipEpisodeError.
	To stop downloading (fatal error), raise PauseDownloadError.
	"""
	
	def download():
		if not crawler.is_init:
			debug_log("D_INIT")
			crawler.init()
			
		if not crawler.html:
			debug_log("D_INIT_IMAGE")
			crawler.init_images()
	
		if not crawler.image:
			debug_log("D_NEXT_PAGE")
			crawler.next_page()
			return
			
		if crawler.page_exists():
			debug_log("D_NEXT_IMAGE")
			print("page {} already exist".format(crawler.ep.total + 1))
			crawler.next_image()
			return
			
		debug_log("D_RESOLVE")
		crawler.resolve_image()
		print("Downloading {} page {}: {}\n".format(
			crawler.ep.title, crawler.ep.total + 1, crawler.image.url))
		debug_log("D_DOWNLOAD")
		crawler.download_image()
		debug_log("D_HANDLE")
		crawler.handle_image()
		debug_log("D_SAVE")
		crawler.save_image()
		debug_log("D_PUB")
		mission_ch.pub("MISSION_PROPERTY_CHANGED", crawler.mission)
		debug_log("D_REST")
		crawler.rest()
		debug_log("D_NEXT_IMAGE")
		crawler.next_image()

	def download_error(er, count):
		t = min(5 * 2 ** count, 600)
		print(f"wait {t} seconds...")
		if is_http(er, code=429):
			# retry doesn't work with 429 error
			sleep(t)
			raise er
		crawler.handle_error(er)
		sleep(t)

	error_loop(download, download_error)

def error_loop(process, handle_error=None, limit=5):
	"""Loop process until error. Has handle error limit."""
	errorcount = 0
	while True:
		try:
			process()
		except Exception as er: # pylint: disable=broad-except
			traceback.print_exc()
			# FIXME: don't increase error count if some bytes are actually downloaded
			errorcount += 1
			if errorcount >= limit:
				raise SkipEpisodeError(always=False) from None
			if handle_error:
				handle_error(er, errorcount)
		# except ExitErrorLoop:
			# break
		else:
			errorcount = 0
