#! python3

"""Comic Crawler."""

import re, traceback
import sys, os, gzip, pprint

from safeprint import safeprint
from collections import OrderedDict
from config import setting, section

import urllib.request
import urllib.parse
from worker import Worker
from html import unescape
		
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
	
	def __init__(self):
		"""set controller"""
		super().__init__()
		
		self.moduleManager = ModuleManager()
		self.missionManager = MissionManager()
		
		self.missions = MissionList().setParent(self)
		self.library = MissionList().setParent(self)
		
		self.downloadWorker = None
		self.analyzeWorkers = set()
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
			"libraryautocheck": "True"
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
