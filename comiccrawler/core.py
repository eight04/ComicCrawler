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
from .error import TooManyRetryError, LastPageError, SkipEpisodeError, ImageExistsError
from .io import content_write, is_file
from .config import setting

default_header = {
	"User-Agent": "Mozilla/5.0 (Windows NT 6.1; WOW64; rv:34.0) Gecko/20100101 Firefox/34.0",
	"Accept-Language": "zh-tw,zh;q=0.8,en-us;q=0.5,en;q=0.3",
	"Accept-Encoding": "gzip, deflate"
}

class Mission(UserWorker):
	"""Mission data class. Contains a mission's information."""
	def __init__(self, title=None, url=None, episodes=None, state="INIT", update=False):
		from .mods import get_module
		
		super().__init__()
		
		self.title = title
		self.url = url
		self.episodes = episodes
		self.state = state
		self.update = update
		self.module = get_module(url)
		if not self.module:
			raise Exception("Get module failed")
		
	def set(self, key, value):
		"""Set new attribute"""
		
		if not hasattr(self, key):
			return
		
		setattr(self, key, value)
		self.bubble("MISSION_PROPERTY_CHANGED", self)

class Episode:
	"""Episode data class. Contains a book's information."""
	
	def __init__(self, title=None, url=None, current_url=None, current_page=0, skip=False, complete=False):
	
		self.title = title
		self.url = url
		self.current_url = current_url
		self.current_page = current_page
		self.skip = skip
		self.complete = complete
	
def getext(byte):
	"""Test the file type according byte stream with imghdr
	
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
	"""Return a safe directory name. Return string."""

	return sub("[/\\\?\|<>:\"\*]","_",s).strip()

def quote_from_match(match):
	"""Quote the match"""
	return quote(match.group())
	
def quote_unicode(s):
	return sub("[\u0080-\uffff \[\]]+", quote_from_match, s)
	
def safeurl(url):
	"""Return a safe url, quote the unicode characters."""
	
	base = search("(https?://[^/]+)", url).group(1)
	path = url.replace(base, "")
	path = quote_unicode(path)
	return base + path
	
def safeheader(header):
	"""Return a safe header, quote the unicode characters."""
	
	for key in header:
		header[key] = quote_unicode(header[key])
	return header
	
def grabber(url, header=None, raw=False, referer=None):
	"""Http works"""
	
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
	
	def parse_content(b):
		if raw:
			return b
			
		# decompress gziped data
		if response.getheader("Content-Encoding") == "gzip":
			b = decompress(b)
		
		# find html defined encoding
		s = b.decode("utf-8", "replace")
		match = search(r"charset=[\"']?([^\"'>]+)", s)
		if match:
			s = b.decode(match.group(1), "replace")
			
		return s
	
	content = parse_content(b)
	
	if setting.getboolean("errorlog"):
		from pprint import pformat
		content_write("~/comiccrawler/grabber.file.log", content)
		content_write("~/comiccrawler/grabber.header.log", "{}\n\n{}".format(
			pformat(request.header_items()),
			pformat(response.getheaders())
		))
	
	return content

def grabhtml(url, header=None, referer=None):
	"""Get html source of given url. Return String."""
	return grabber(url, header, False, referer)

def grabimg(url, header=None, referer=None):
	"""Return byte stream."""	
	return grabber(url, header, True, referer)
	
def download(mission, savepath, thread=None):
	"""download worker"""
		
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
		raise
	else:
		mission.set("state", "FINISHED")
			
def crawl(mission, savepath, thread):
	"""Start mission download. This method will call cls.crawlpage()
	for each episode.
	
	"""
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
		mission.update = False

def crawlpage(ep, downloader, savepath, fexp, thread):
	"""Crawl all pages of an episode.
	
	Grab image into savepath. To exit the method, raise LastPageError.
	
	Should define error handler for grabimg failed. Note the error by
	setting episode.errorpages, episode.currentpagenumber, episode.
	totalpages, episode.currentpageurl.
	
	"""
	import time, os, os.path
	
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
					raise TooManyRetryError
					
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
					ep.currentpagenumber))
					
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
			if is_file(fn):
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
					ep.currentpagenumber))
					
		except Exception as er:
			safeprint("Crawl page error")
			print_exc()
			
			errorcount += 1
			
			if errorcount >= 10:
				raise TooManyRetryError
			
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
		
		# Rest after each page
		thread.wait(getattr(downloader, "rest", 0))
		
def analyze(mission, thread=None):	
	"""Analyze mission.url"""

	mission.set("state", "ANALYZING")
	
	try:
		analyze_info(mission, mission.module, thread)
		
	except WorkerExit:
		mission.set("state", "PAUSE")
		raise
		
	except Exception as er:
		mission.set("state", "ERROR")
		print_exc()
		thread.bubble("ANALYZE_FAILED", (mission, er))
		
	else:
		if mission.update:
			mission.set("state", "UPDATE")
		else:
			mission.set("state", "ANALYZED")
			
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
			
		for ep in episodes:
			if ep.url not in old_ep:
				mission.episodes.append(ep)
				mission.update = True
	else:
		mission.episodes = episodes
		
	# remove duplicate
	remove_duplicate_episode(mission)
	
	safeprint("Analyzing success!")
