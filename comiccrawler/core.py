#! python3

from imghdr import what
from os import mkdir, listdir
from os.path import normpath, split, join
from re import sub, search
from urllib.parse import quote
from urllib.request import Request, urlopen
from gzip import decompress
from worker import WorkerExit, UserWorker
from traceback import print_exc
from html import unescape

from .safeprint import safeprint
from .error import (
	LastPageError, SkipEpisodeError, ImageExistsError, PauseDownloadError,
	ModuleError
)
from .io import content_write, is_file
from .config import setting

import pprint

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

def quote_from_match(match):
	"""Return quoted match.group."""
	return quote(match.group())
	
def quote_unicode(s):
	"""Quote unicode characters."""
	return sub(r"[\u0080-\uffff]+", quote_from_match, s)
	
def safeurl(url):
	"""Return a safe url, quote the unicode characters."""
	base = search("(https?://[^/]+)", url).group(1)
	path = url.replace(base, "")
	path = quote_unicode(path)
	return base + path
	
def safeheader(header):
	"""Return a safe header, quote the unicode characters."""
	for key, value in header.items():
		if not isinstance(value, str):
			raise Exception(
				"header value must be str!\n" + pprint.pformat(header)
			)
		header[key] = quote_unicode(value)
	return header
	
def grabber(url, header=None, raw=False, referer=None, errorlog=None):
	"""Request url, return text or bytes of the content."""
	
	url = safeurl(url)
	url = unescape(url)
	
	if header is None:
		header = {}
		
	for key in default_header:
		if key not in header:
			header[key] = default_header[key]
			
	if referer:
		header["Referer"] = referer
			
	header = safeheader(header)
	
	request = Request(url, headers=header)
	response = urlopen(request, timeout=20)
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
		if not errorlog:
			errorlog = "~/comiccrawler"
		from pprint import pformat
		content_write(join(errorlog, "grabber.file.log"), content)
		content_write(join(errorlog, "grabber.header.log"), "{}\n\n{}".format(
			pformat(request.header_items()),
			pformat(response.getheaders())
		))
	
	return content

def grabhtml(url, header=None, referer=None, errorlog=None):
	"""Get html source of given url. Return String."""
	return grabber(url, header, False, referer, errorlog)

def grabimg(url, header=None, referer=None, errorlog=None):
	"""Return byte stream."""	
	return grabber(url, header, True, referer, errorlog)
	
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
			fexp = safefilepath(ep.title) + "_{:03}"
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

def crawlpage(ep, downloader, savepath, fexp, thread):
	"""Crawl all pages of an episode.
	
	To complete current episode, raise LastPageError.
	To skip current episode, raise SkipEpisodeError.
	To stop downloading (fatal error), raise PauseDownloadError.
	"""
	import time, os, os.path
	
	# Check if the mission has been downloaded
	page_exists = set()
	if os.path.isdir(savepath):
		for file in  os.listdir(savepath):
			if os.path.isfile(os.path.join(savepath, file)):
				page_exists.add(os.path.splitext(file)[0])
	
	if not ep.current_page:
		ep.current_page = 1
		
	if not ep.current_url:
		ep.current_url = ep.url
		
	imgurls = None
	# if we can get all img urls from the first page
	if hasattr(downloader, "getimgurls"):
		errorcount = 0
		while not imgurls:
			try:
				header = getattr(downloader, "header", None)
				html = thread.sync(grabhtml, ep.url, header)
				imgurls = thread.sync(downloader.getimgurls, html, ep.url)
				
				if not imgurls:
					raise Exception("imgurls is empty")
					
			except Exception as er:
				safeprint("Get imgurls failed")
				print_exc()
				errorcount += 1
				
				if errorcount >= 10:
					raise Exception("Retry too many times!")
					
				if hasattr(downloader, "errorhandler"):
					try:
						downloader.errorhandler(er, ep)
					except Exception as er:
						safeprint("Error handler error")
						print_exc()
						
				thread.wait(5)
			
		if len(imgurls) < ep.current_page:
			raise LastPageError

	# crawl all pages
	errorcount = 0
	while True:
		try:
			header = getattr(downloader, "header", None)
			
			if not imgurls:
				safeprint("Crawling {} page {}...".format(ep.title,
					ep.current_page))
					
				# getimgurl method
				html = thread.sync(
					grabhtml,
					ep.current_url,
					header
				)
				
				imgurl = thread.sync(
					downloader.getimgurl,
					html,
					ep.current_url,
					ep.current_page,
				)
				
				nextpageurl = thread.sync(
					downloader.getnextpageurl,
					html, 
					ep.current_url,
					ep.current_page, 
				)
				
			else:
				# getimgurls method
				imgurl = imgurls[ep.current_page - 1]
				if ep.current_page < len(imgurls):
					nextpageurl = ep.current_url
				else:
					nextpageurl = None
			
			# generate file name
			fn = fexp.format(ep.current_page)
			
			# file already exist
			if fn in page_exists:
				raise ImageExistsError
				
			safeprint("Downloading {} page {}: {}".format(
					ep.title, ep.current_page, imgurl))
					
			oi = thread.sync(grabimg, imgurl, header, ep.current_url)
			
			# check image type
			ext = getext(oi)
			
			if not ext:
				raise TypeError("Invalid image type.")
				
		except ImageExistsError:
			safeprint("page {} already exist".format(
					ep.current_page))
					
		except Exception as er:
			safeprint("Crawl page error")
			print_exc()
			
			errorcount += 1
			
			if errorcount >= 10:
				raise Exception("Retry too many times!")
			
			if hasattr(downloader, "errorhandler"):
				try:
					downloader.errorhandler(er, ep)
					
				except Exception as er:
					safeprint("In error handler")
					print_exc()
			
			thread.wait(5)
			continue
			
		else:
			# everything is ok, save image
			content_write(join(savepath, "{}.{}".format(fn, ext)), oi)
			
		# something have to rewrite, check currentpage url rather than
		# nextpage. Cuz sometime currentpage doesn't exist either.
		if not nextpageurl:
			raise LastPageError
			
		ep.current_url = nextpageurl
		ep.current_page += 1
		
		errorcount = 0
		
		if fn not in page_exists:
			# Rest after each page
			thread.wait(getattr(downloader, "rest", 0))
		
def analyze(mission, thread=None):	
	"""Analyze mission.url"""

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
	"""remove duplicate episode"""
	
	s = set()
	cleanList = []
	for ep in mission.episodes:
		if ep.url not in s:
			s.add(ep.url)
			cleanList.append(ep)
	mission.episodes = cleanList
			
def analyze_info(mission, downloader, thread):
	"""Analyze mission url."""		
	safeprint("Start analyzing {}".format(mission.url))
	
	complete = mission.state == "FINISHED"
	mission.set("state", "ANALYZING")
	
	header = getattr(downloader, "header", None)
	
	html = thread.sync(grabhtml, mission.url, header)
	
	if not mission.title:
		mission.title = downloader.gettitle(html, mission.url)
		
	episodes = thread.sync(downloader.getepisodelist, html, mission.url)
	
	if not episodes:
		raise Exception("episodes are empty")
	
	# Check if re-analyze
	if mission.episodes:
		old_ep = set()
		for ep in mission.episodes:
			old_ep.add(ep.url)
			
		update = False
			
		for ep in episodes:
			if ep.url not in old_ep:
				mission.episodes.append(ep)
				update = True
		
		if update:
			mission.set("state", "UPDATE")
			
		elif complete:
			mission.set("state", "FINISHED")
			
		else:
			mission.set("state", "ANALYZED")

	else:
		mission.episodes = episodes
		mission.set("state", "ANALYZED")
		
	# remove duplicate
	remove_duplicate_episode(mission)
	
	safeprint("Analyzing success!")
