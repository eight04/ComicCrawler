#! python3

"""Comic Crawler."""

VERSION = "20140709"

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
		
	def printList(self):
		"""print mission list"""
		for m in self.q:
			print(m.title)
			
	def getList(self):
		return [m.title for m in self.q]
		
	def load(self, path):
		import pickle
		try:
			f = open(path, "rb")
		except FileNotFoundError:
			print("no lib file")
			return
		self.q = pickle.load(f)
		
	def save(self, path):
		import pickle
		f = open(path, "wb")
		pickle.dump(self.q, f)
		

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
		epList = downloader.getepisodelist(html, url=mission.url)
		if not mission.episodeList:
			mission.episodeList = epList
		else:
			for ep in epList:
				for oep in mission.episodeList:
					if oep.url == ep.url:
						break
				else:
					mission.episodeList.append(ep)
					mission.update = True
			if not mission.update:
				return

		if not mission.episodelist:
			raise Exception("get episode list failed!")
		
		safeprint("analyzed succeed!")
		if mission.update:
			mission.state_(UPDATE)
		else:
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
		
class Library:
	""" Library"""
	
	def __init__(self, crawler):
		self.libraryList = FreeQue()
		self.crawler = crawler
		
		self.libraryList.load("library.dat")
		
	def add(self, mission):
		self.libraryList.put(mission)
		
	def remove(self, mission):
		self.libraryList.remove(mission)
		
	def checkUpdate(self):
		def worker():
			for m in self.libraryList.q:
				self.crawler._analyze(m)
			_evtcallback("LIBRARY_CHECK_UPDATE_FINISHED")
		threading.Thread(target=worker).start()

	def sendToDownloadManager(self):
		for m in self.libraryList.q:
			if m.update:
				self.crawler.addmission(m)

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
	library = Library(crawler)
	safeprint("Valid domains: " + " ".join(dlmm.getdlHolder()))
	safeprint("Library list: " + " ".join(library.libraryList.getList()))
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
			command = None
			if not u.startswith("http"):
				command, sep, u = u.partition(" ")
			if command == "lib":
				safeprint(" ".join(library.libraryList.getList()))
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
					library.add(m)
					crawler.start()
					crawler.thread.join()
		print("")
		