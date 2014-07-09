#! python3

"""Comic Crawler."""

VERSION = "20140609"

import urllib.request
import urllib.parse
import urllib.error
import re
import os
import threading
import importlib
import pickle
import time
import configparser
import imghdr

# imghdr issue: http://bugs.python.org/issue16512
def _test_jpeg(h, f):
	if h[:2] == b"\xff\xd8":
		return "JPEG"
	return None
imghdr.tests.append(_test_jpeg)

def _test_swf(h, f):
	if h[:3] == b"CWS" or h[:3] == b"FWS":
		return "SWF"
	return None
imghdr.tests.append(_test_swf)

def _test_psd(h, f):
	if h[:4] == b"8BPS":
		return "PSD"
	return None
imghdr.tests.append(_test_psd)

def _test_rar(h, f):
	if h[:7] == b"Rar!\x1a\x07\x00":
		return "RAR"
	return None
imghdr.tests.append(_test_rar)

from safeprint import safeprint

INIT = 0
ANALYZED = 1
DOWNLOADING = 2
PAUSE = 3
FINISHED = 4
ERROR = 5
INTERRUPT = 6


_eventhandler = None
def _evtcallback(msg, *arg):
	"""GUI Message control"""
	
	if callable(_eventhandler):
		_eventhandler(msg, *arg)
	
"""
def getimgext(url):
	url = url.lower()
	if ".png" in url:
		return "png"
	if ".gif" in url:
		return "gif"
	if ".swf" in url:
		return "swf"
	if ".psd" in url:
		return "psd"
	if ".rar" in url:
		return "rar"
	return "jpg"
"""

def getext(byte):
	"""Test the file type according byte stream with imghdr"""
	
	r = imghdr.what("", byte)
	if not r:
		return None
		
	if r.lower() == "jpeg":
		return "jpg"
	return r.lower()
			
def createdir(path):
	"""Create folder of filepath. 
	
	This function can handle sub-folder like 
	"this_doesnt_exist\sure_this_doesnt_exist_either\I_want_to_create_this"
	
	"""
	
	dirpath = path.split("\\")
	create = ""
	for d in dirpath:
		create += d + "\\"
		try:
			os.mkdir(create)
		except Exception as er:
			_evtcallback("MAKEDIR_EXC", er)

def safefilepath(s):
	"""Return a safe dir name. Return string."""

	return re.sub("[/\\\?\|<>:\"\*]","_",s).strip()
	
def safeurl(url):
	"""Return a safe url, quote the unicode characters."""
	
	base = re.search("(https?://[^/]+)", url).group(1)
	path = url.replace(base, "")
	def u(match):
		return urllib.parse.quote(match.group())
	path = re.sub("[\u0080-\uffff]+", u, path)
	return base + path
	
def grabhtml(url, hd={}, encode=None):
	"""Get html source of given url. Return String."""
	
	url = safeurl(url)
	req = urllib.request.Request(url,headers=hd)
	rs = urllib.request.urlopen(req, timeout=20)
	ot = rs.read()
	
	# auto cookie controler
	"""
	from http.cookies import SimpleCookie
	c = SimpleCookie()
	
	try:
		c.load(hd["Cookie"])
	except Exception:
		pass
	try:
		c.load(rs.getheader("Set-Cookie"))
	except Exception:
		pass
	cookie = ""
	for k in c:
		cookie += "{}={};".format(k, c[k].value)
	hd["Cookie"] = cookie
	"""
	
	if encode is None:
		try:
			encode = re.search("<meta charset=(\"|')([^\"']+)(\"|')").group(2)
			return ot.decode(encode, "replace")
		except Exception:
			pass
		try:
			encode = re.search("charset=([^\"'>]+)",ot.decode("utf-8","replace")).group(1)
			return ot.decode(encode, "replace")
		except Exception:
			return ot.decode("utf-8", "replace")
	else:
		return ot.decode(encode,"replace")

def grabimg(url, hd={}):
	"""Return byte stream."""
	
	url = safeurl(url)
	req = urllib.request.Request(url, headers=hd)
	rs = urllib.request.urlopen(req, timeout=20)
	return rs.read()

	
class FreeQue:
	"""Mission queue data class."""
	
	q = []	# the list which save the missions
	
	def empty(self):
		"""return true if list is empty"""
		return not self.q
	
	def put(self, item):
		"""append item"""
		self.q.append(item)
		_evtcallback("MISSIONQUE_ARRANGE")
		
	def lift(self, items, reverse=False):
		"""Move items to the top."""
		a = [ i for i in self.q if i in items ]
		b = [ i for i in self.q if i not in items ]
		if not reverse:
			self.q = a + b
		else:
			self.q = b + a
		_evtcallback("MISSIONQUE_ARRANGE")
	
	def drop(self, items):
		"""Move items to the bottom."""
		self.lift(items, reverse=True)
		
	def remove(self, items):
		"""Delete specify items."""
		self.q = [ i for i in self.q if i not in items]
		_evtcallback("MISSIONQUE_ARRANGE")

	def take(self, n=1):
		"""Return a list containing n valid missions. If n <= 1 return a valid 
		mission.
		"""
		if n <= 1:
			for i in self.q:
				if i.state != FINISHED:
					return i
			return None
		else:
			s = []
			for i in self.q:
				if i.state != FINISHED:
					s.append(i)
				if len(s) == n:
					return s
			return s or None
			
	def cleanfinished(self):
		"""delete fished missions"""
		self.q = [ i for i in self.q if i.state is not FINISHED ]
		_evtcallback("MISSIONQUE_ARRANGE")

class Mission:
	"""Mission data class. Contains a mission's information."""
	
	def __init__(self):
		self.title = ""
		self.url = ""
		self.episodelist = []
		self.state = INIT
		# self.statechangecallback = None
		self.downloader = None
		self.lock = threading.Lock()
		
	def state_(self, state=None):
		if not state:
			return self.state
		self.state = state
		_evtcallback("MISSION_STATE_CHANGE", self)
			
	def __getstate__(self):
		state = self.__dict__.copy()
		del state["downloader"]
		del state["lock"]
		# if "statechangecallback" in state:
			# del state["statechangecallback"]
		return state
		
	def __setstate__(self, state):
		self.__dict__.update(state)
		self.lock = threading.Lock()
		
	def setTitle(self, title):
		self.title = title
		_evtcallback("MISSION_TITLE_CHANGE", self)

class Episode:
	"""Episode data class. Contains a book's information."""
	
	def __init__(self):
		self.title = ""
		self.firstpageurl = ""
		self.currentpageurl = ""
		self.currentpagenumber = 0
		self.skip = False
		self.complete = False
		self.error = False
		self.errorpages = 0
		self.totalpages = 0

		
class DownloadWorker:
	def __init__(self, crawler):
	
		def worker():
			while True:
				mission = crawler.missionque.take()
				# print(mission)
				if mission is None:
					crawler.stop()
					safeprint("All download complete!")
					break
					
				try:
					mission.lock.acquire()
					mission.state_(DOWNLOADING)
					self.download(mission)
				except (ExitSignalError, InterruptError):
					print("kill download worker")
					mission.state_(PAUSE)
				except TooManyRetryError:
					safeprint("Too many retry")
					mission.state_(PAUSE)
					crawler.missionque.drop((mission,))
				except Exception as er:
					import traceback
					er_message = traceback.format_exc()
					print("worker terminate!\n{}".format(er_message))
					crawler.stop()
					mission.state_(ERROR)
					_evtcallback("WORKER_TERMINATED", mission, er, er_message)
				finally:
					mission.lock.release()
					
				if self._stop:
					# safeprint("Download worker killed.")
					break
		
		self._stop = False
		self.savepath = crawler.savepath.rstrip("\\/")
		self.threading = threading.Thread(target=worker)
		self.crawler = crawler
		
		self.threading.start()

	def download(self, mission):
		"""Start mission download. This method will call self.crawlpage()
		for each episode.
		
		"""
		
		safeprint("total {} episode.".format(len(mission.episodelist)))
		for ep in mission.episodelist:
			if ep.skip or ep.complete:
				continue
				
			# deside wether to generate Episode folder, or it will put every 
			# image file in one folder. Ex. pixiv.net
			if ("noepfolder" in mission.downloader.__dict__ and 
					mission.downloader.noepfolder):
				efd = "{}\\{}\\".format(self.savepath, safefilepath(mission.title))
				fexp = safefilepath(ep.title) + "_{:03}"
			else:
				efd = "{}\\{}\\{}\\".format(self.savepath, safefilepath(mission.title), safefilepath(ep.title))
				fexp = "{:03}"
			createdir(efd)
			
			safeprint("Downloading ep {}".format(ep.title))
			try:
				self.crawlpage(ep, efd, mission, fexp)
			except LastPageError:
				safeprint("Episode download complete!")
				print("")
				ep.complete = True
				self.crawler.save()
				"""
			except InterruptError:
				safeprint("Download interrupted.")
				mission.state_(PAUSE)
				self.crawler.save()
				break
				"""
		else:
			safeprint("Mission complete!")
			mission.state_(FINISHED)
			
			# run after download
			command = self.crawler.runafterdownload
			if not command:
				return
			try:
				import subprocess
				subprocess.call((command, "{}/{}".format(self.savepath, safefilepath(mission.title))))
			except Exception as er:
				safeprint("failed to run process: {}".format(er))

	def crawlpage(self, ep, savepath, mission, fexp):
		"""Crawl all pages of an episode.
		
		Grab image into savepath. To exit the method, raise LastPageError.
		
		Should define error handler for grabimg failed. Note the error by
		setting episode.errorpages, episode.currentpagenumber, episode.
		totalpages, episode.currentpageurl.
		
		"""
		
		downloader = mission.downloader
		
		if not ep.currentpagenumber:
			ep.currentpagenumber = 1
		if not ep.currentpageurl:
			ep.currentpageurl = ep.firstpageurl
			
		imgurls = None
		if "getimgurls" in downloader.__dict__:
			# we can get all img urls from first page
			errorcount = 0
			while not imgurls:
				try:
					html = grabhtml(ep.firstpageurl, hd=downloader.header)
					imgurls = downloader.getimgurls(html, url=ep.firstpageurl)
				except Exception as er:
					safeprint("get imgurls failed: {}".format(er))
					# import traceback
					# print(traceback.format_exc())
					errorcount += 1
					if errorcount >= 10:
						# self.crawler.missionque.drop((mission, ))
						raise TooManyRetryError
					if "errorhandler" in downloader.__dict__:
						downloader.errorhandler(er, ep)
					self.pausecallback(mission)
					time.sleep(5)
		ep.imgurls = imgurls
		
		# downloaded list for later use
		import os
		downloadedlist = [ i.rpartition(".")[0] for i in os.listdir(savepath) ]
		
		# crawl all pages
		errorcount = 0
		while True:
			safeprint("Crawling {} {} page {}...".format(mission.title, 
					ep.title, ep.currentpagenumber))
			try:
				if not imgurls:
					# getimgurl method
					html = grabhtml(ep.currentpageurl, hd=downloader.header)
					
					imgurl = downloader.getimgurl(html, 
							page=ep.currentpagenumber, url=ep.currentpageurl)
					nextpageurl = downloader.getnextpageurl(ep.currentpagenumber, 
							html, url=ep.currentpageurl)
					try:
						imgurl, header = imgurl
					except Exception:
						header = downloader.header
				else:
					# getimgurls method
					imgurl = imgurls[ep.currentpagenumber - 1]
					header = downloader.header
					nextpageurl = ep.currentpagenumber < len(imgurls)
				
				# generate file name
				# ext = getimgext(imgurl)
				fn = fexp.format(ep.currentpagenumber)
				
				# file already exist
				if fn in downloadedlist:
					raise FileExistError
					
				safeprint("Downloading image: {}".format(imgurl))
				oi = grabimg(imgurl,hd=header)
				
				# check image type
				ext = getext(oi)
				if not ext:
					raise Exception("Invalid image type.")
					
			except FileExistError:
				safeprint("...page {} already exist".format(
						ep.currentpagenumber))
						
			except Exception as er:
				safeprint("Crawl page error: {}".format(er or type(er)))
				errorcount += 1
				if errorcount >= 10:
					# self.crawler.missionque.drop((mission, ))
					raise TooManyRetryError
				self.pausecallback(mission)
				
				if not downloader.errorhandler(er, ep):
					time.sleep(5)
				continue
				
			else:
				# everything is ok, save image
				f = open(savepath + fn + "." + ext, "wb")
				f.write(oi)
				f.close()
				
			# call pause
			self.pausecallback(mission)
				
			if not nextpageurl:
				ep.complete = True
				raise LastPageError
			ep.currentpageurl = nextpageurl
			ep.currentpagenumber += 1
			errorcount = 0
			print("")
	
	def stop(self):
		self._stop = True
		
	def pausecallback(self, mission=None):
		"""Hook to stop worker thread."""		
		if self._stop:
			raise InterruptError
			
	def join(self):
		"""thread join method."""
		self.threading.join()

class ComicCrawler:
	"""Downloader class. Do all the analyze job and control workers
	
	The main class of comiccrawler.
	"""
	
	def __init__(self, modulemanager=None, eventhandler=None):
		self.missionque = FreeQue()
		self.state = PAUSE
		self.skippagewhenfailed = False
		self.dlmm = modulemanager
		self.thread = None
		self.alzthread = None
		
		global _eventhandler
		_eventhandler = eventhandler
		
		self.loadconfig()
		

	def loadconfig(self):
		config = configparser.ConfigParser(interpolation=None)
		config["DEFAULT"] = {
			"savepath": "download",
			"runafterdownload": ""
		}
		
		config.read("setting.ini", "utf-8-sig")
		
		self.savepath = config["DEFAULT"]["savepath"]
		self.runafterdownload = config["DEFAULT"]["runafterdownload"]

		with open("setting.ini", "w", encoding="utf-8") as f:
			config.write(f)
		
	def addmission(self, mission):
		self.missionque.put(mission)
	
	def start(self):
		if self.missionque.empty():
			safeprint("Misison que is empty.")
			return
			
		if self.state == DOWNLOADING:
			safeprint("Crawler is downloading.")
			return
			
		self.state = DOWNLOADING
		self.thread = DownloadWorker(self)
		safeprint("Crawler started.")
		
	def stop(self):
		self.state = PAUSE
		# self.available.clear()
		if self.thread:
			self.thread.stop()
		safeprint("Crawler stopped.")
	
	def analyze(self, mission, callback=None):
		def worker():
			try:
				self._analyze(mission)
			except Exception as er:
				safeprint("Analyzed failed: {}".format(er))
				# import traceback
				# safeprint(traceback.format_exc())
				mission.state = ERROR
				_evtcallback("ANALYZED_FAILED", mission, er)
			else:
				_evtcallback("ANALYZED_SUCCESS", mission)

		t = threading.Thread(target=worker)
		t.start()
		self.alzthread = t
		
	def _analyze(self, mission):
		"""Analyze mission url."""
		
		safeprint("start analyzing {}".format(mission.url))
		
		downloader = mission.downloader
		html = grabhtml(mission.url, hd=downloader.header)
		# print(html)
		
		mission.title = downloader.gettitle(html, url=mission.url)
		mission.episodelist = downloader.getepisodelist(html, url=mission.url)
		if not mission.episodelist:
			raise Exception("get episode list failed!")
		
		safeprint("analyzed succeed!")
		mission.state = ANALYZED
		
	def save(self):
		"""Save mission que."""
		try:
			f = open("save.dat", "wb")
		except Exception as er:
			_evtcallback("DAT_SAVE_FAILED", er)
		else:
			pickle.dump(self.missionque.q, f)
			print("Session saved success.")
		
	def load(self):
		try:
			f = open("save.dat", "rb")
			s = pickle.load(f)
		except Exception as er:
			_evtcallback("DAT_LOAD_FAILED", er)
		else:
			for m in s:
				m.downloader = self.dlmm.getDownloader(m.url)
				self.addmission(m)
			print("Session loaded success.")
		
		
		
class FileExistError(Exception):
	def __str__(self):
		return "FileExistError"
			

class BandwidthExceedError(Exception):
	def __str__(self):
		return "BandwidthExceedError"
	
	
class LastPageError(Exception):
	def __str__(self):
		return "LastPageError"

		
class ExitSignalError(Exception):
	def __str__(self):
		return repr(self)
		
class InterruptError(Exception):
	def __str__(self):
		return repr(self)

class TooManyRetryError(Exception):
	def __str__(self):
		return repr(self)
		
class DLModuleManager:
	"""Import all the downloader module.
	
	DLModuleManger will automatic import all modules in the same directory 
	which prefixed with filename "cc_".
	
	"""
	
	def __init__(self):
		self.dlHolder = {}
		modsfile = [mod.replace(".py","") for mod in os.listdir() if re.search("^cc_.+\.py$", mod)]
		mods = [importlib.import_module(mod) for mod in modsfile]
		for d in mods:
			for dm in d.domain:
				self.dlHolder[dm] = d
		self.mods = mods
		self.loadconfig()
		
	def loadconfig(self):
		"""Load setting.ini and set up module.
		
		There's a utf-8 issue with configparser:
		http://bugs.python.org/issue14311
		"""
	
		config = configparser.ConfigParser(interpolation=None)
		config.read("setting.ini", "utf-8-sig")
		for d in self.mods:
			if "loadconfig" in d.__dict__:
				d.loadconfig(config)
		with open("setting.ini", "w", encoding="utf-8") as f:
			config.write(f)
		safeprint("Load setting.ini success!")
		
	def getdlHolder(self):
		"""Return downloader dictionary."""
		return [key for key in self.dlHolder]
		
	def validUrl(self,url):
		"""Return if the url is valid and in downloaders domain."""
		
		dm = re.search("https?://([^/]+?)(:\d+)?/", url)
		if dm is None:
			return False
		dm = dm.group(1)
		for d in self.dlHolder:
			if d in dm:
				return True
		return False
		
	def getDownloader(self, url):
		"""Return the downloader mod of spect url or return None"""
		
		dm = re.search("https?://([^/]+?)(:\d+)?/", url)
		if dm is None:
			return None
		dm = dm.group(1)
		for d in self.dlHolder:
			if d in dm:
				return self.dlHolder[d]
		return None
		

if __name__ == "__main__":
	dlmm = DLModuleManager()
	crawler = ComicCrawler(dlmm)
	safeprint("Valid domains: " + " ".join(dlmm.getdlHolder()))
	print("")
	while True:
		try:
			u = input("This is Comic Crawler version " + VERSION + "\n"
				" - Paste an url and press enter to start download.\n"
				" - or use Ctrl+Z to exit.\n"
				">>> ")
		except EOFError:
			break
		else:
			downloader = dlmm.getDownloader(u)
			if downloader is None:
				print("Unknown url: {}\n".format(u))
			else:
				# construct a mission
				m = Mission()
				m.url = u
				m.downloader = downloader
				print("Analyzing url: {}".format(m.url))
				crawler.analyze(m)
				crawler.alzthread.join()
				if m.state == ANALYZED:
					crawler.addmission(m)
					crawler.start()
					crawler.thread.join()
		print("")
		