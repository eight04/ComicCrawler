#! python3

"""Comic Crawler."""

import re
from safeprint import safeprint

import urllib.request
import urllib.parse
import urllib.error
from urllib.error import HTTPError, URLError
import threading
import collections
from worker import Worker, StopWorker

import traceback

oldStateCode = {
	0: "INIT",
	1: "ANALYZED",
	2: "DOWNLOADING",
	3: "PAUSE",
	4: "FINISHED",
	5: "ERROR",
	6: "INTERRUPT",
	7: "UPDATE",
	8: "ANALYZING"
}
	
class CrawlerError(Exception): pass

class ImageExistsError(CrawlerError): pass

class LastPageError(CrawlerError): pass

class TooManyRetryError(CrawlerError): pass

class EmptyImageError(CrawlerError): pass

class SkipEpisodeError(CrawlerError): pass

class ModuleError(CrawlerError): pass

def extend(dict, *args):
	"""extend(dict1, dict2)
	
	copy dict2 into dict1 with no overwrite
	"""
	for dict2 in args:
		for key, value in dict2.items():
			if key not in dict:
				dict[key] = value
	
def getext(byte):
	"""Test the file type according byte stream with imghdr
	
	imghdr issue: http://bugs.python.org/issue16512
	"""
	
	import imghdr
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
		
	return None
			
def createdir(path):
	"""Create folder of filepath. 
	
	This function can handle sub-folder like 
	"this_doesnt_exist\sure_this_doesnt_exist_either\I_want_to_create_this"
	"""
	import os, os.path
	
	path = os.path.normpath(path)
	
	try:
		os.mkdir(path)
	except FileExistsError:
		pass
	except FileNotFoundError as er:
		a, b = os.path.split(path)
		createdir(a)
		createdir(path)
	
def safefilepath(s):
	"""Return a safe directory name. Return string."""

	return re.sub("[/\\\?\|<>:\"\*]","_",s).strip()
	
def safeurl(url):
	"""Return a safe url, quote the unicode characters."""
	
	base = re.search("(https?://[^/]+)", url).group(1)
	path = url.replace(base, "")
	def u(match):
		return urllib.parse.quote(match.group())
	path = re.sub("[\u0080-\uffff \[\]]+", u, path)
	# safeprint(base + path)
	return base + path
	
def safeheader(header):
	"""Return a safe header, quote the unicode characters."""
	
	def u(match):
		return urllib.parse.quote(match.group())
	for key in header:
		header[key] = re.sub("[\u0080-\uffff]+", u, header[key])
		
	return header

def grabber(url, header={}, encode=False):
	"""Http works"""
	
	defaultHeader = {
		"User-Agent": "Mozilla/5.0 (Windows NT 6.1; WOW64; rv:32.0) Gecko/20100101 Firefox/32.0"
	}
	url = safeurl(url)
	safeprint(url)
	# bugged when header contains non latin character...
	extend(header, defaultHeader)
	header = safeheader(header)
	
	req = urllib.request.Request(url, headers=header)
	rs = urllib.request.urlopen(req, timeout=20)
	ot = rs.read()
	
	if not encode:
		return ot
		
	# find html defined encoding
	html = ot.decode("utf-8", "replace")
	r = re.search(r"charset=[\"']?([^\"'>]+)", html)
	if r:
		encode = r.group(1)
		return ot.decode(encode, "replace")
	return html

def grabhtml(url, hd={}, encode="utf-8"):
	"""Get html source of given url. Return String."""
	
	return grabber(url, hd, encode)

def grabimg(url, hd={}):
	"""Return byte stream."""
	
	return grabber(url, hd)


class Mission:
	"""Mission data class. Contains a mission's information."""
	title = ""
	url = ""
	episodelist = []
	state = "INIT"
	update = False

class MissionContainer(Worker):
	"""Mission container. Load mission from JSON"""
	def __init__(self):
		"""Create lock"""
		super().__init__()
		
		self.mission = None
		self.downloader = None
		self.lock = threading.Lock()
		
	def set(self, *args, **kwargs):
		"""Set new attribute, may replace setTitle later."""
		
		# safeprint(args, kwargs)
		key = None
		for arg in args:
			# safeprint(arg)
			if key is None:
				key = arg
			else:
				kwargs[key] = arg
				key = None
		
		dirty = False
		for key, value in kwargs.items():
			# safeprint(key, value)
			if hasattr(self.mission, key):
				setattr(self.mission, key, value)
				dirty = True
				
		if dirty:
			self.bubble("MISSION_PROPERTY_CHANGED", self)

class Episode:
	"""Episode data class. Contains a book's information."""
	
	title = ""
	firstpageurl = ""
	currentpageurl = ""
	currentpagenumber = 0
	skip = False
	complete = False
	error = False
	errorpages = 0
	totalpages = 0
		
class DownloadWorker(Worker):
	"""The main core of Comic Crawler"""

	def __init__(self, mission=None, savepath="."):
		"""set the mission"""
		super().__init__()
		
		self.mission = mission
		self.savepath = savepath
	
	def worker(self):
		"""download worker"""
		
		# warning there is a deadlock, 
		# never do mission.lock.acquire in callback...
		safeprint("DownloadWorker start downloading " + self.mission.mission.title)
		try:
			self.mission.lock.acquire()
			self.mission.set("state", "DOWNLOADING")
			print("set")
			self.download(self.mission.mission, self.savepath, self.mission.downloader)
		except StopWorker as er:
			self.mission.set("state", "PAUSE")
			self.bubble("DOWNLOAD_PAUSE", self.mission)
			raise er
		except Exception as er:
			traceback.print_exc()
			self.mission.set("state", "ERROR")
			self.bubble("DOWNLOAD_ERROR", self.mission)
			# self.callback(self.mission, er)
		else:
			self.mission.set("state", "FINISHED")
			self.bubble("DOWNLOAD_FINISHED", self.mission)
			# self.callback(self.mission)
		finally:
			self.mission.lock.release()
			
	def download(self, mission, savepath, downloader):
		"""Start mission download. This method will call cls.crawlpage()
		for each episode.
		
		"""
		import os.path
		
		safeprint("total {} episode.".format(len(mission.episodelist)))
		for ep in mission.episodelist:
			if ep.skip or ep.complete:
				continue
				
			# deside wether to generate Episode folder, or it will put every 
			# images file in one folder. Ex. pixiv.net
			if ("noepfolder" in downloader.__dict__ and 
					downloader.noepfolder):
				efd = os.path.join(savepath, safefilepath(mission.title))
				fexp = safefilepath(ep.title) + "_{:03}"
			else:
				efd = os.path.join(savepath, safefilepath(mission.title), 
						safefilepath(ep.title))
				fexp = "{:03}"
			
			safeprint("Downloading ep {}".format(ep.title))
			try:
				self.crawlpage(ep, efd, mission, fexp, downloader)
			except LastPageError:
				safeprint("Episode download complete!")
				print("")
				ep.complete = True
				self.bubble("DOWNLOAD_EP_COMPLETE", (mission, ep))
				# _evtcallback("DOWNLOAD_EP_COMPLETE", mission, ep)
			except SkipEpisodeError:
				safeprint("Something bad happened, skip the episode.")
				ep.skip = True
				continue
		else:
			safeprint("Mission complete!")
			# mission.state_(FINISHED)
			mission.update = False

	def crawlpage(self, ep, savepath, mission, fexp, downloader):
		"""Crawl all pages of an episode.
		
		Grab image into savepath. To exit the method, raise LastPageError.
		
		Should define error handler for grabimg failed. Note the error by
		setting episode.errorpages, episode.currentpagenumber, episode.
		totalpages, episode.currentpageurl.
		
		"""
		import time, os, os.path
		
		if not ep.currentpagenumber:
			ep.currentpagenumber = 1
		if not ep.currentpageurl:
			ep.currentpageurl = ep.firstpageurl
			
		imgurls = None
		if "getimgurls" in downloader.__dict__:
			# we can get all img urls from first page
			errorcount = 0
			while True:
				try:
					html = self.waitChild(grabhtml, ep.firstpageurl, downloader.header)
					imgurls = self.waitChild(downloader.getimgurls, html, url=ep.firstpageurl)
					
					if not imgurls:
						raise EmptyImageError
						
				except (LastPageError, SkipEpisodeError, StopWorker) as er:
					raise er
					
				except HTTPError as er:
					safeprint("get imgurls failed: {}".format(er))
					# traceback.print_exc()
					errorcount += 1
					if errorcount >= 10:
						raise TooManyRetryError
					if "errorhandler" in downloader.__dict__:
						downloader.errorhandler(er, ep)
					self.wait(5)
				else:
					break
				
		ep.imgurls = imgurls
		
		if imgurls and len(imgurls) < ep.currentpagenumber:
			raise LastPageError

		# some file already in directory
		createdir(savepath)
		downloadedlist = [ i.rpartition(".")[0] for i in os.listdir(savepath) ]
		
		# crawl all pages
		errorcount = 0
		while True:
			safeprint("Crawling {} {} page {}...".format(mission.title, 
					ep.title, ep.currentpagenumber))
			try:
				if not imgurls:
					# getimgurl method
					html = self.waitChild(
						grabhtml, 
						ep.currentpageurl, 
						hd=downloader.header
					)
					
					imgurl = self.waitChild(
						downloader.getimgurl, 
						html, 
						url=ep.currentpageurl,
						page=ep.currentpagenumber, 
					)
					
					nextpageurl = self.waitChild(
						downloader.getnextpageurl,
						ep.currentpagenumber, 
						html, 
						url=ep.currentpageurl
					)
					
					if type(imgurl) is tuple:
						imgurl, header = imgurl
					else:
						header = downloader.header
				else:
					# getimgurls method
					imgurl = imgurls[ep.currentpagenumber - 1]
					header = downloader.header
					nextpageurl = ep.currentpagenumber < len(imgurls)
				
				# generate file name
				fn = fexp.format(ep.currentpagenumber)
				
				# file already exist
				if fn in downloadedlist:
					raise ImageExistsError
					
				safeprint("Downloading page {}: {}".format(
						ep.currentpagenumber, imgurl))
						
				oi = self.waitChild(grabimg, imgurl, hd=header)
				
				# check image type
				ext = getext(oi)
				if not ext:
					raise TypeError("Invalid image type.")
					
			except ImageExistsError:
				safeprint("...page {} already exist".format(
						ep.currentpagenumber))
						
			except StopWorker as er:
				raise er
				
			except Exception as er:
				safeprint("Crawl page error: {}".format(er or type(er)))
				errorcount += 1
				if errorcount >= 10:
					raise TooManyRetryError
				downloader.errorhandler(er, ep)
				
				self.wait(5)
				continue
				
			else:
				# everything is ok, save image
				with open(os.path.join(savepath, "{}.{}".format(fn, ext)), "wb") as f:
					f.write(oi)
				
			# something have to rewrite, check currentpage url rather than
			# nextpage. Cuz sometime currentpage doesn't exist either.
			if not nextpageurl:
				ep.complete = True
				raise LastPageError
			ep.currentpageurl = nextpageurl
			ep.currentpagenumber += 1
			errorcount = 0
			print("")
	
class AnalyzeWorker(Worker):
	"""Analyze the mission.url, also the core of Comic Crawler"""

	def __init__(self, parent, mission=None):
		"""set mission"""
		super().__init__(parent)
		
		self.mission = mission
	
	def worker(self):
		"""analyze worker"""
		
		try:
			self.mission.lock.acquire()
			self.mission.set("state", "ANALYZING")
			self.analyze(self.mission.mission, self.mission.downloader)
		except Exception as er:
			self.mission.set("state", "ERROR")
			import traceback
			er_message = traceback.format_exc()
			self.mission.error = er_message
			safeprint(er_message)
			self.bubble("ANALYZE_FAILED", self.mission)
		else:
			if self.mission.update:
				self.mission.set("state", "UPDATE")
			else:
				self.mission.set("state", "ANALYZED")
			# self.callback(self.mission)
			self.bubble("ANALYZE_FINISHED", self.mission)
		finally:
			self.mission.lock.release()

	def removeDuplicateEP(self, mission):
		"""remove duplicate episode"""
		
		dict = {}
		for ep in mission.episodelist:
			dict[ep.firstpageurl] = ep
			
		mission.episodelist = [ep for key, ep in dict]
			
	def analyze(self, mission, downloader):
		"""Analyze mission url."""
		
		safeprint("start analyzing {}".format(mission.url))

		print("grabbing html")
		html = self.waitChild(grabhtml, mission.url, hd=downloader.header)
		print("getting title")
		mission.title = downloader.gettitle(html, url=mission.url)
		print("getting episode list")
		epList = self.waitChild(downloader.getepisodelist, html, url=mission.url)
		if not mission.episodelist:
			# new mission
			mission.episodelist = epList
		else:
			# re-analyze, put new ep into eplist
			for ep in epList:
				for oep in mission.episodelist:
					if oep.firstpageurl == ep.firstpageurl:
						# found
						break
				else:
					mission.episodelist.append(ep)
			# check if there are incomplete ep
			for ep in mission.episodelist:
				if not ep.complete and not ep.skip:
					mission.update = True
					break
		
		if not mission.episodelist:
			raise Exception("get episode list failed!")
		
		# remove duplicate
		self.removeDuplicateEP(mission)
		
		safeprint("analyzed succeed!")

class MissionList(Worker):
	"""Mission queue data class."""
	
	def __init__(self, savepath=None):
		super().__init__()
		self.q = []
		self.savepath = savepath
		
	def contains(self, mission):
		for m in self.q:
			if q.url == mission.url:
				return True
		return False
	
	def isEmpty(self):
		"""return true if list is empty"""
		return not self.q
	
	def put(self, item):
		"""append item"""
		self.q.append(item)
		self.addChild(item)
		self.bubble("MISSIONQUE_ARRANGE", self)
		
	def lift(self, items, reverse=False):
		"""Move items to the top."""
		a = [ i for i in self.q if i in items ]
		b = [ i for i in self.q if i not in items ]
		if not reverse:
			self.q = a + b
		else:
			self.q = b + a
		self.bubble("MISSIONQUE_ARRANGE", self)
	
	def drop(self, items):
		"""Move items to the bottom."""
		self.lift(items, reverse=True)
		
	def remove(self, *items):
		"""Delete specify items."""
		for item in items:
			if not item.lock.acquire(blocking=False):
				raise RuntimeError("Mission already in use")
			else:
				self.q.remove(item)
				self.removeChild(item)
				item.lock.release()
		self.bubble("MISSIONQUE_ARRANGE", self)
		self.bubble("MESSAGE", "Deleted {} mission(s)".format(len(items)))

	def take(self, n=1):
		"""Return a list containing n valid missions. If n <= 1 return a valid 
		mission.
		"""
		
		s = []
		for missionContainer in self.q:
			if missionContainer.mission.state != "FINISHED":
				s.append(missionContainer)
			if len(s) == n:
				return s if n > 1 else s[0]
		return None
			
	def cleanfinished(self):
		"""delete fished missions"""
		self.q = [ i for i in self.q if i.mission.state != "FINISHED"]
		safeprint(self.q)
		self.bubble("MISSIONQUE_ARRANGE", self)
		
	def printList(self):
		"""print mission list"""
		for m in self.q:
			print(m.title)
			
	def getList(self):
		"""return title list"""
		return [m.title for m in self.q]
		
	def load(self):
		"""unpickle list from file"""
		if not self.savepath:
			return
		import pickle
		try:
			f = open(self.savepath, "rb")
		except FileNotFoundError:
			print(self.savepath + " not exists.")
			return
			
		self.q = []
		missions = pickle.load(f)
		for mission in missions:
			# backward compact
			if not hasattr(mission, "update"):
				setattr(mission, "update", False)
				
			if mission.state in oldStateCode:
				mission.state = oldStateCode[mission.state]
			
			missionContainer = MissionContainer()
			missionContainer.mission = mission
			
			self.put(missionContainer)
		
		# debug
		self.removeDuplicate()
		self.bubble("MISSIONQUE_ARRANGE", self)
		
	def removeDuplicate(self):
		dict = {}
		removed = []
		for missionContainer in self.q:
			if missionContainer.mission.url in dict:
				removed.append(missionContainer)
			else:
				dict[missionContainer.mission.url] = True
		self.remove(*removed)
		
	def save(self):
		"""pickle list to file"""
		if not self.savepath:
			return
		import pickle
		f = open(self.savepath, "wb")
		missions = []
		for missionContainer in self.q:
			missions.append(missionContainer.mission)
		pickle.dump(missions, f)
		
	def getByURL(self, url):
		"""Take mission with specify url"""
		
		for mission in self.q:
			if mission.mission.url == url:
				return mission
		return None

class ConfigManager:
	"""Load config for other classes"""

	def __init__(self, path):
		"""set config file path"""
		import configparser as cp
		self.path = path
		self.config = cp.ConfigParser(interpolation=None)
		
		self.load()

	def get(self):
		"""return config"""
		return self.config
		
	def load(self):
		"""read config from file
		
		There's a utf-8 issue with configparser:
		http://bugs.python.org/issue14311
		"""
		self.config.read(self.path, "utf-8-sig")
		
	def save(self):
		with open(self.path, "w", encoding="utf-8") as f:
			self.config.write(f)
		
	@classmethod
	def apply(cls, config, dict, overwrite=False):
		"""ConfigManager.apply(dict1, dict2, overwrite)
		
		copy dict2 into dict1
		"""
		for key, value in dict.items():
			if not overwrite and key in config:
				continue
			config[key] = value
		return

class DownloadManager(Worker):
	"""DownloadManager class. Maintain the mission list."""
	
	def __init__(self, configManager=None, moduleManager=None):
		"""set controller"""
		super().__init__()
		
		self.configManager = configManager
		self.moduleManager = moduleManager
		# self.missionPool = MissionPool("missions.dat")
		missions = MissionList("save.dat")
		self.addChild(missions)
		self.missions = missions
		
		library = MissionList("library.dat")
		self.addChild(library)
		self.library = library
		
		self.downloadWorker = None
		self.libraryWorker = None
		self.analyzeWorkers = []
		
		self.conf()
		self.load()
		
	def conf(self):
		"""Load config from controller. Set default"""		
		import os.path
		
		conf = self.configManager
		self.setting = conf.get()["DEFAULT"]
		default = {
			"savepath": "download",
			"runafterdownload": "",
			"libraryautocheck": "true"
		}
		# conf.apply(self.setting, default)
		extend(self.setting, default)
		
		# clean savepath
		self.setting["savepath"] = os.path.normpath(self.setting["savepath"])
		
	def addURL(self, url):
		"""add url"""
		
		mission = self.library.getByURL(url)
		if not mission:
			mission = Mission()
			mission.url = url
		self.analyze(mission)
		
	def analyze(self, mission):
		"""Analyze mission"""
		
		missionContainer = MissionContainer()
		missionContainer.mission = mission
		missionContainer.downloader = self.moduleManager.getDownloader(mission.url)
		worker = self.createChild(AnalyzeWorker, missionContainer).start()
		self.analyzeWorkers.append(worker)
		
	def addMission(self, mission):
		"""add mission"""
		
		if self.missions.contains(mission):
			raise MissionDuplicateError
		self.missions.put(mission)
		
	def removeMission(self, *args):
		"""delete mission"""
	
		self.missions.remove(args)
	
	def startDownload(self):
		"""Start downloading"""
		if self.downloadWorker and self.downloadWorker.running:
			return
			
		mission = self.missions.take()
		if not mission:
			raise Error("All download completed")
		safeprint("Start download " + mission.mission.title)
		self.downloadWorker = self.createChild(DownloadWorker, mission, self.setting["savepath"]).start()
		
	def stopDownload(self):
		"""Stop downloading"""
		if self.downloadWorker and self.downloadWorker.running:
			self.stop(self.downloadWorker)
			safeprint("Stop download " + self.downloadWorker.mission.mission.title)
		
	def startCheckUpdate(self):
		"""Start check library update"""
		if self.libraryWorker and self.libraryWorker.running:
			return
		
		mission = self.library.take()
		self.libraryWorker = self.createChild(AnalyzeWorker, mission).start()
		
	def worker(self):
		"""Event loop"""
		while True:
			self.wait()
			# print("loop")
		
	def onMessage(self, message, param, thread):
		"""Override"""
		safeprint("DownloadManager onMessage", message)
		
		if message == "DOWNLOAD_FINISHED":
			command = self.setting["runafterdownload"]
			if command:
				try:
					from subprocess import call
					call((command, "{}/{}".format(self.setting["savepath"], safefilepath(thread.mission.title))))
				except Exception as er:
					safeprint("failed to run process: {}".format(er))
					
			mission = self.missions.take()
			if not mission:
				safeprint("All download completed")
			else:
				self.downloadWorker = self.createChild(DownloadWorker, mission).start()
					
		if message == "DOWNLOAD_ERROR":
			mission = self.missions.take()
			if not mission:
				safeprint("All download completed")
			else:
				self.downloadWorker = self.createChild(DownloadWorker, mission).start()
			
		if message == "DOWNLOAD_PAUSE":
			pass
		
		if message == "CHILD_THREAD_END":
			if thread == self.libraryWorker:
				mission = self.library.take()
				if mission:
					self.libraryWorker = self.createChild(AnalyzeWorker, mission).start()
				
			if thread in self.analyzeWorkers:
				if param.mission.state == "ERROR":
					self.bubble("ANALYZE_FAILED", param)
				else:
					self.bubble("ANALYZE_FINISHED", param)
				self.analyzeWorkers.remove(thread)

		super().onMessage(message, param, thread)
	
	def save(self):
		"""Save mission que."""
		
		try:
			self.missions.save()
			self.library.save()
		except OSError as er:
			self.bubble("SESSION_SAVE_FAILED", er)
		else:
			print("Session saved success.")
		
	def load(self):
		"""load mission que"""
		
		try:
			self.missions.load()
			self.library.load()
		except OSError as er:
			self.bubble("SESSION_LOAD_FAILED", er)
		else:
			for m in self.missions.q:
				m.downloader = self.moduleManager.getDownloader(m.mission.url)
			for m in self.library.q:
				m.downloader = self.moduleManager.getDownloader(m.mission.url)
			print("Session loaded success.")
			
		self.replaceDuplicate()
		
	def replaceDuplicate(self):
		"""replace duplicate with library one"""
		
		for missionContainer in self.missions.q:
			for libraryContainer in self.library.q:
				if missionContainer.mission.url == libraryContainer.mission.url:
					missionContainer.mission = libraryContainer.mission

	def addLibrary(self, mission):
		"""add mission"""
		
		if self.library.contains(mission):
			raise MissionDuplicateError
		self.library.put(mission)
		
	def removeLibrary(self, *missions):
		"""remove missions"""
		
		self.library.remove(missions)
		
	def addMissionUpdate(self):
		"""Add updated mission to download list"""
		for mission in self.library.q:
			self.addMission(mission)
		
		
class ModuleManager:
	"""Import all the downloader module.
	
	DLModuleManger will automatic import all modules in the same directory 
	which name prefixed with "cc_".
	
	"""
	
	def __init__(self, configManager = None):
		import os
		self.configManager = configManager
		self.dlHolder = {}
		self.mods = []
		self.mod_dir = os.path.dirname(os.path.realpath(__file__))
		
		self.loadconfig()
		self.loadMods()
		self.registHolders()
		
	def loadMods(self):
		"""Load mods to self.mods"""
		import importlib, os
		
		for f in os.listdir(self.mod_dir):
			if not re.search("^cc_.+\.py$", f):
				continue
			mod = f.replace(".py","")
			self.mods.append(importlib.import_module(mod))
		
	def registHolders(self):
		"""Regist domain with mod to self.dlHolder"""
		
		for mod in self.mods:
			for url in mod.domain:
				self.dlHolder[url] = mod

		
	def loadconfig(self):
		"""Load setting.ini and set up module.
		"""
	
		config = self.configManager.get()
		for d in self.mods:
			if "loadconfig" in d.__dict__:
				d.loadconfig(config)
		
	def getdlHolder(self):
		"""Return downloader dictionary."""
		return [key for key in self.dlHolder]
		
	def validUrl(self,url):
		"""Return if the url is valid and in downloaders domain."""
		
		if self.getDownloader(url):
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
		
class Main(Worker):
	"""workflow logic"""
	
	def worker(self):
		"""Load class -> view -> unload class"""
		
		self.loadClasses()
		self.view()
		self.unloadClasses()
	
	def loadClasses(self):
		"""Load classes."""
		
		self.configManager = ConfigManager("setting.ini")
		self.moduleManager = ModuleManager(configManager=self.configManager)
		self.downloadManager = self.createChild(
			DownloadManager,
			configManager = self.configManager,
			moduleManager = self.moduleManager
		).start()
		
		self.downloadManager.load()
		
	def unloadClasses(self):
		"""Unload classes."""
		
		# wait download manager stop
		if self.downloadManager.running:
			self.downloadManager.stop()
			self.downloadManager.join()
		self.downloadManager.save()
		
		# save config
		self.configManager.save()
		
	def view(self):
		"""Override."""
		pass

if __name__ == "__main__":
	
	class CLI:
		def __init__(self):
			import os
			
			self.workingDir = os.getcwd()
			self.scriptDir = os.path.dirname(os.path.realpath(__file__))
			os.chdir(self.scriptDir)
			
			self.configManager = ConfigManager("setting.ini")
			self.moduleManager = ModuleManager(configManager=self.configManager)
			
			from sys import argv
			if len(argv) <= 1:
				self.downloadManager = DownloadManager(
					configManager=self.configManager,
					moduleManager=self.moduleManager
				).start()
				
				self.inputLoop()
			
			elif argv[1] == "domains":
				self.listDomains()
			elif argv[1] == "download":	
				kw = {
					"url": argv[2],
					"savepath": self.workingDir
				}
				if len(argv) >= 5 and argv[3] == "-d":
					kw["savepath"] = os.path.join(self.workingDir, argv[4])
				
				self.start(**kw)
				
		def start(self, url=None, savepath="."):
			if not url:
				return
				
			mission = Mission()
			mission.url = url
			mission.downloader = self.moduleManager.getDownloader(url)
			AnalyzeWorker().analyze(mission)
			DownloadWorker().download(mission, savepath)
			
		def listDomains(self):
			safeprint("Valid domains:\n{}".format(", ".join(self.moduleManager.getdlHolder())))
			
		def inputLoop(self):
			while True:
				s = input(">>> ")
				
	CLI()
