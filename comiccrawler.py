#! python3

"""Comic Crawler."""

import re
import pickle
import traceback
import sys, os, gzip, pprint

from safeprint import safeprint
from collections import OrderedDict
from config import setting, section

import urllib.request
import urllib.parse
import urllib.error
from urllib.error import HTTPError, URLError
import threading
import collections
from worker import Worker, WorkerSignal
from html import unescape

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

class MissionDuplicateError(CrawlerError): pass

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
		
	if h[:4] == b"\x1A\x45\xDF\xA3":
		return "mkv"
		
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

def grabber(url, header=None, encode=False):
	"""Http works"""
	
	defaultHeader = {
		"User-Agent": "Mozilla/5.0 (Windows NT 6.1; WOW64; rv:34.0) Gecko/20100101 Firefox/34.0",
		"Accept-Language": "zh-tw,zh;q=0.8,en-us;q=0.5,en;q=0.3",
		"Accept-Encoding": "gzip, deflate"
	}
	url = safeurl(url)
	url = unescape(url)
	# bugged when header contains non latin character...
	extend(header, defaultHeader)
	header = safeheader(header)
	
	req = urllib.request.Request(url, headers=header)
	rs = urllib.request.urlopen(req, timeout=20)
	ot = rs.read()
	
	ret = ot
	
	# decompress gziped data
	if rs.getheader("Content-Encoding") == "gzip":
		ot = gzip.decompress(ot)
	
	if encode:
		# find html defined encoding
		ret = ot.decode("utf-8", "replace")
		r = re.search(r"charset=[\"']?([^\"'>]+)", ret)
		if r:
			encode = r.group(1)
			ret = ot.decode(encode, "replace")
	else:
		ret = ot
			
	if setting.getboolean("errorlog"):
		errorlog("grabber.header.log", "{}\n\n{}\n\n{}".format(
			url, pprint.pformat(req.header_items()),
			pprint.pformat(rs.getheaders())
		))
		errorlog("grabber.file.log", ot)
		
	return ret

def grabhtml(url, hd={}, encode="utf-8"):
	"""Get html source of given url. Return String."""
	return grabber(url, hd, encode)

def grabimg(url, hd={}):
	"""Return byte stream."""	
	return grabber(url, hd)
	
def errorlog(path, msg):
	"""Log something to file"""
	if type(msg) is str:
		with open(path, "w", encoding="utf-8") as file:
			file.write(msg)
	else:
		with open(path, "wb") as file:
			file.write(msg)
		
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
		self.error = None
		
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

	def __init__(self, mission, savepath):
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
			self.mission.set("state", "DOWNLOADING")
			self.download(self.mission.mission, self.savepath, self.mission.downloader)
		except WorkerSignal as er:
			self.mission.set("state", "PAUSE")
			self.bubble("DOWNLOAD_PAUSE", self.mission)
			raise er
		except Exception as er:
			traceback.print_exc()
			self.mission.set("state", "ERROR")
			if type(er) is TooManyRetryError:
				self.bubble("DOWNLOAD_TOO_MANY_RETRY", self.mission)
			self.bubble("DOWNLOAD_ERROR", self.mission)
		else:
			self.mission.set("state", "FINISHED")
			self.bubble("DOWNLOAD_FINISHED", self.mission)
			
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
				ep.complete = True
				self.bubble("DOWNLOAD_EP_COMPLETE", (mission, ep))
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
						raise RuntimeError("Image url is null")
						
				except (LastPageError, SkipEpisodeError, WorkerSignal) as er:
					raise er
					
				except Exception as er:
					safeprint("Get imgurls failed:", er)
					traceback.print_exc()
					errorcount += 1
					if errorcount >= 10:
						raise TooManyRetryError
					if "errorhandler" in downloader.__dict__:
						try:
							downloader.errorhandler(er, ep)
						except SkipEpisodeError as er:
							raise er
						except Exception as er:
							safeprint("Error handler error:", er)
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
			try:
				if not imgurls:
					safeprint("Crawling {} page {}...".format(ep.title,
						ep.currentpagenumber))
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
					
				safeprint("Downloading {} page {}: {}".format(
						ep.title, ep.currentpagenumber, imgurl))
						
				oi = self.waitChild(grabimg, imgurl, hd=header)
				
				# check image type
				ext = getext(oi)
				if not ext:
					raise TypeError("Invalid image type.")
					
			except ImageExistsError:
				safeprint("page {} already exist".format(
						ep.currentpagenumber))
						
			except WorkerSignal as er:
				raise er
				
			except Exception as er:
				safeprint("Crawl page error: {}".format(er or type(er)))
				errorcount += 1
				if errorcount >= 10:
					raise TooManyRetryError
				try:
					downloader.errorhandler(er, ep)
				except Exception as er:
					safeprint("In error handler:", er)
				
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
			
			# Rest after each page
			if hasattr(downloader, "rest"):
				self.wait(downloader.rest)
	
class AnalyzeWorker(Worker):
	"""Analyze the mission.url, also the core of Comic Crawler"""

	def __init__(self, mission=None):
		"""set mission"""
		super().__init__()
		
		self.mission = mission
	
	def worker(self):
		"""analyze worker"""
		
		try:
			self.mission.lock.acquire()
			self.analyze(self.mission)
		except Exception as er:
			self.mission.set("state", "ERROR")
			self.mission.error = er
			traceback.print_exc()
			self.bubble("ANALYZE_FAILED", self.mission)
		else:
			self.bubble("ANALYZE_FINISHED", self.mission)
		finally:
			self.mission.lock.release()

	def removeDuplicateEP(self, mission):
		"""remove duplicate episode"""
		
		s = set()
		cleanList = []
		for ep in mission.episodelist:
			if ep.firstpageurl not in s:
				s.add(ep.firstpageurl)
				cleanList.append(ep)
		mission.episodelist = cleanList
			
	def analyze(self, missionContainer):
		"""Analyze mission url."""		
		mission = missionContainer.mission
		downloader = missionContainer.downloader

		safeprint("Start analyzing {}".format(mission.url))
		missionContainer.set("state", "ANALYZING")
		
		html = self.waitChild(grabhtml, mission.url, hd=downloader.header)
		
		if not mission.title:
			mission.title = downloader.gettitle(html, url=mission.url)
			
		epList = self.waitChild(downloader.getepisodelist, html, url=mission.url)
		
		# Remove duplicate episode
		urls = set()
		duplicate = set()
		
		for ep in epList:
			if ep.firstpageurl in urls:
				duplicate.add(ep)
			else:
				urls.add(ep.firstpageurl)
				
		epList = [ep for ep in epList if ep not in duplicate]
		
		# Check if re-analyze
		if not mission.episodelist:
			mission.episodelist = epList
			missionContainer.set("state", "ANALYZED")
		else:
			epIndex = {}
			
			for ep in epList:
				epIndex[ep.firstpageurl] = ep
			
			for ep in mission.episodelist:
				if ep.firstpageurl in epIndex:
					newEp = epIndex[ep.firstpageurl]
					newEp.currentpageurl = ep.currentpageurl
					newEp.currentpagenumber = ep.currentpagenumber
					newEp.skip = ep.skip
					newEp.complete = ep.complete
					newEp.errorpages = ep.errorpages
				else:
					epList.append(ep)
			mission.episodelist = epList
			
			# check if there are incomplete ep
			for ep in mission.episodelist:
				if not ep.complete and not ep.skip:
					mission.update = True
					missionContainer.set("state", "UPDATE")
					break
			else:
				missionContainer.set("state", "FINISHED")
		
		if not mission.episodelist:
			raise Exception("get episode list failed!")
		
		# remove duplicate
		self.removeDuplicateEP(mission)
		
		safeprint("Analyzing success!")

class MissionList(Worker):
	"""Wrap OrderedDict. Add commonly using method."""
	
	def __init__(self):
		super().__init__()
		
		self.data = OrderedDict()
		
	def reset(self):
		for key, item in self.data.items():
			if item.lock.acquire(blocking=False):
				item.set("state", "ANALYZE_INIT")
				item.lock.release()
		
	def contains(self, item):
		return item.mission.url in self.data
		
	def containUrl(self, url):
		return url in self.data
	
	def isEmpty(self):
		"""return true if list is empty"""
		return not self.data
	
	def append(self, *items):
		"""append item"""
		for item in items:
			if self.contains(item):
				# raise KeyError("Duplicate item")
				print("Bug? Found duplicate item? " + item.mission.url)
			else:
				self.data[item.mission.url] = item
		self.bubble("MISSIONQUE_ARRANGE", self)
		
	def lift(self, *items):
		"""Move items to the top."""
		for item in reversed(items):
			self.data.move_to_end(item.mission.url, last=False)
		self.bubble("MISSIONQUE_ARRANGE", self)
	
	def drop(self, *items):
		"""Move items to the bottom."""
		for item in items:
			self.data.move_to_end(item.mission.url)
		self.bubble("MISSIONQUE_ARRANGE", self)
		
	def remove(self, *items):
		"""Delete specify items."""
		if not items:
			return
			
		for item in items:
			if item.lock.acquire(blocking=False):
				try:
					del self.data[item.mission.url]
				finally:
					item.lock.release()
			else:
				self.bubble("MISSION_REMOVE_FAILED", item)
				raise RuntimeError("Mission already in use")
				
		self.bubble("MISSIONQUE_ARRANGE", self)
		safeprint("Deleted {} mission(s)".format(len(items)))
		
	def takeAnalyze(self):
		"""Return a pending mission"""
		for key, m in self.data.items():
			if m.mission.state == "ANALYZE_INIT":
				return m

	def take(self):
		"""Return a list containing n valid missions. If n <= 1 return a valid 
		mission.
		"""		
		for key, item in self.data.items():
			if item.mission.state not in ["FINISHED", "DOWNLOADING"]:
				if item.lock.acquire(blocking=False):
					return item
				
	def clear(self):
		self.data.clear()
			
	def cleanfinished(self):
		"""delete fished missions"""
		removed = []
		for key, item in self.data.items():
			if item.mission.state == "FINISHED":
				removed.append(item)
		self.remove(*removed)

	def get(self, url):
		"""Take mission with specify url"""
		return self.data[url]

class Timer(Worker):
	"""Autosave mission list"""
	
	def __init__(self, callback=None, timeout=0, infinite=False):
		super().__init__()
		
		self.callback = callback
		self.timeout = timeout
		self.infinite = infinite
		
	def worker(self):
		while True:
			self.wait(self.timeout)
			self.callback()
			if not self.infinite:
				break

class DownloadManager(Worker):
	"""DownloadManager class. Maintain the mission list."""
	
	def __init__(self, moduleManager=None):
		"""set controller"""
		super().__init__()
		
		self.moduleManager = moduleManager
		
		self.missions = MissionList().setParent(self)
		self.library = MissionList().setParent(self)
		
		self.downloadWorker = None
		self.libraryWorker = None
		
		self.autosave = Timer(
			callback = self.save,
			timeout = 5 * 60,
			infinite = True
		).setParent(self)
		
		# Message listeners
		@self.listen
		def DOWNLOAD_TOO_MANY_RETRY(param, sender):
			self.missions.drop(param)
		
		@self.listen("DOWNLOAD_FINISHED")
		@self.listen("DOWNLOAD_ERROR")
		def afterDownload(param, sender):
			param.lock.release()
			mission = self.missions.take()
			if not mission:
				safeprint("All download completed")
			else:
				worker = DownloadWorker(mission, setting["savepath"])
				worker.setParent(self).start()
				self.downloadWorker = worker
				
		@self.listen
		def DOWNLOAD_PAUSE(mission, thread):
			mission.lock.release()
		
		@self.listen
		def DOWNLOAD_FINISHED(param, thread):
			command = setting["runafterdownload"]
			if command:
				try:
					from subprocess import call
					call((command, "{}/{}".format(setting["savepath"], safefilepath(thread.mission.title))))
				except Exception as er:
					safeprint("Failed to run process: {}".format(er))
				
		@self.listen("ANALYZE_FAILED")
		@self.listen("ANALYZE_FINISHED")
		def afterAnalyze(param, sender):
			if sender is self.libraryWorker:
				if param.mission.update:
					self.library.lift(param)
					
				mission = self.library.takeAnalyze()
				if mission:
					self.libraryWorker = self.createChild(AnalyzeWorker, mission).start()
					print("OK next")
				
				if not param.error:
					return False
		
		# @self.listen
		# def DOWNLOAD_EP_COMPLETE(param, thread):
			# self.save()
			
	def worker(self):
		self.conf()
		self.load()
		if setting.getboolean("libraryautocheck"):
			self.startCheckUpdate()
		self.autosave.start()
		while True:
			self.wait()
		
	def conf(self):
		"""Load config from controller. Set default"""		
		import os.path
		
		default = {
			"savepath": "download",
			"runafterdownload": "",
			"libraryautocheck": True
		}
		section("DEFAULT", default)
		
		setting["savepath"] = os.path.normpath(setting["savepath"])
		
	def addURL(self, url):
		"""add url"""
		if not url:
			return
		try:
			item = self.library.get(url)
		except KeyError:
			mission = Mission()
			mission.url = url
			item = MissionContainer().setParent(self)
			item.mission = mission
			item.downloader = self.moduleManager.getDownloader(url)
		AnalyzeWorker(item).setParent(self).start()
		
	def addMission(self, mission):
		"""add mission"""
		if self.missions.contains(mission):
			raise MissionDuplicateError
		self.missions.append(mission)
		
	def removeMission(self, *args):
		"""delete mission"""
	
		self.missions.remove(args)
	
	def startDownload(self):
		"""Start downloading"""
		if self.downloadWorker and self.downloadWorker.running:
			return
			
		mission = self.missions.take()
		if not mission:
			safeprint("所有任務已下載完成")
			return
		safeprint("Start download " + mission.mission.title)
		self.downloadWorker = self.createChild(DownloadWorker, mission, setting["savepath"]).start()
		
	def stopDownload(self):
		"""Stop downloading"""
		if self.downloadWorker and self.downloadWorker.running:
			self.downloadWorker.stop()
			safeprint("Stop download " + self.downloadWorker.mission.mission.title)
		
	def startCheckUpdate(self):
		"""Start check library update"""
		if self.libraryWorker and self.libraryWorker.running:
			return
			
		self.library.reset()
		mission = self.library.takeAnalyze()
		if mission:
			self.libraryWorker = self.createChild(AnalyzeWorker, mission).start()
		
	def saveFile(self, savepath, missionList):
		"""Save mission list"""
		list = []
		
		for key, item in missionList.data.items():
			list.append(item.mission)
			
		file = open(savepath, "wb")
		pickle.dump(list, file)
		
	def save(self):
		"""Save mission que."""
		try:
			self.saveFile("save.dat", self.missions)
			self.saveFile("library.dat", self.library)
		except OSError as er:
			safeprint("Couldn't save session")
		safeprint("Saved")
			
	def loadFile(self, savepath):
		"""Load .dat from savepath"""
		file = open(savepath, "rb")
		missions = pickle.load(file)
		file.close()
		list = []
		
		for mission in missions:
			# backward compatibility
			if not hasattr(mission, "update"):
				setattr(mission, "update", False)
				
			if mission.state in oldStateCode:
				mission.state = oldStateCode[mission.state]
				
			# Program closed incorrectly last time
			if mission.state == "DOWNLOADING":
				mission.state = "PAUSE"
			
			item = MissionContainer().setParent(self)
			item.mission = mission
			item.downloader = self.moduleManager.getDownloader(mission.url)
			list.append(item)
			
		return list
		
	def load(self):
		"""Load mission que"""
		try:
			items = self.loadFile("save.dat")
		except OSError as er:
			safeprint("Couldn't load save.dat")
		else:
			self.missions.clear()
			self.missions.append(*items)
		
		try:
			items = self.loadFile("library.dat")
		except OSError as er:
			safeprint("Couldn't load library.dat")
		else:
			self.library.clear()
			self.library.append(*items)

		self.replaceDuplicate()
		
	def replaceDuplicate(self):
		"""replace duplicate with library one"""
		for key, item in self.missions.data.items():
			if self.library.contains(item):
				self.missions.data[key] = self.library.data[key]

	def addLibrary(self, mission):
		"""add mission"""
		if self.library.contains(mission):
			raise MissionDuplicateError
		self.library.append(mission)
		
	def removeLibrary(self, *missions):
		"""remove missions"""
		self.library.remove(*missions)
		
	def addMissionUpdate(self):
		"""Add updated mission to download list"""
		for key, item in self.library.data.items():
			if item.mission.update:
				try:
					self.addMission(item)
				except MissionDuplicateError:
					pass
		
class ModuleManager:
	"""Import all the downloader module.
	
	DLModuleManger will automatic import all modules in the same directory 
	which name prefixed with "cc_".
	
	"""
	
	def __init__(self):
		import os
		self.dlHolder = {}
		self.mods = []
		self.mod_dir = os.path.dirname(os.path.realpath(__file__))
		
		self.loadMods()
		self.registHolders()
		self.loadconfig()
		
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
		for mod in self.mods:
			if hasattr(mod, "config"):
				mod.config = section(mod.name, mod.config)
			if hasattr(mod, "loadconfig"):
				mod.loadconfig()
		
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
		
		dm = re.search("^https?://([^/]+?)(:\d+)?/", url)
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
		
		self.moduleManager = ModuleManager()
		self.downloadManager = self.createChild(
			DownloadManager,
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
		
	def view(self):
		"""Override."""
		pass

if __name__ == "__main__":
	workingDir = os.getcwd()
	scriptDir = os.path.dirname(os.path.realpath(__file__))
	os.chdir(scriptDir)
	
	moduleManager = ModuleManager()
	
	if len(sys.argv) <= 1:
		sys.exit("Need more arguments")
		
	elif sys.argv[1] == "domains":
		safeprint("Valid domains:\n{}".format(", ".join(moduleManager.getdlHolder())))
		
	elif sys.argv[1] == "download":	
		url = sys.argv[2]
		savepath = workingDir
		if len(sys.argv) >= 5 and sys.argv[3] == "-d":
			savepath = os.path.join(workingDir, sys.argv[4])
		
		mission = Mission()
		mission.url = url
		container = MissionContainer()
		container.mission = mission
		container.downloader = moduleManager.getDownloader(url)
		
		AnalyzeWorker(container).run()
		DownloadWorker(container, savepath).run()
