#! python3

"""Comic Crawler."""

import subprocess, traceback

from worker import Worker, UserWorker
from json import JSONEncoder
from os import path
from collections import OrderedDict

from .safeprint import safeprint
from .config import setting, section
from .core import Mission, Episode, download, analyze, createdir

def shallow(dict, exclude=None):
	new_dict = {}
	for key in dict:
		if not exclude or key not in exclude:
			new_dict[key] = dict[key]
	return new_dict
	
def content_write(file, content):
	file = path.expanduser(file)
	createdir(dirname(file))
	with open(file, "w", encoding="utf-8") as f:
		f.write(content)
		
def content_read(file):
	file = path.expanduser(file)
	with open(file, "r", encoding="utf-8") as f:
		return f.read()

class MissionPoolEncoder(JSONEncoder):
	def default(self, object):
		if isinstance(object, Mission):
			return shallow(vars(object), exclude=["module"])
		
		if isinstance(object, Episode):
			return shallow(vars(object))
			
		if isinstance(object, set):
			return list(object)
			
		return super().default(object)
		
class MissionListEncoder(JSONEncoder):
	def default(self, obj):
		if isinstance(obj, OrderedDict):
			return list(obj)
		
		if isinstance(obj, Mission):
			return obj.url
			
		return super().default(obj)

class MissionManager(UserWorker):
	"""Save, load missions from files"""
	def __init__(self):
		super().__init__()
		
		self.pool = {}
		self.view = OrderedDict()
		self.library = OrderedDict()
		
		try:
			self.load()
		except Exception:
			pass

	def save(self):
		content_write("~/comiccrawler/pool.json", json.dumps(self.pool, cls=MissionPoolEncoder))
		content_write("~/comiccrawler/view.json", json.dumps(self.view, cls=MissionListEncoder))
		content_write("~/comiccrawler/library.json", json.dumps(self.library, cls=MissionListEncoder))
		
	def load(self):
		pool = json.loads(content_read("~/comiccrawler/pool.json"))
		view = json.loads(content_read("~/comiccrawler/view.json"))
		library = json.loads(content_read("~/comiccrawler/library.json"))
		
		for m_data in pool:
			# build episodes
			episodes = []
			for ep_data in m_data["episodes"]:
				episodes.append(Episode(**ep_data))
			m_data["episodes"] = episodes
			mission = Mission(**m_data)
			self._add(mission)
			
		self.add("view", *[self.pool[url] for url in view])
		self.add("library", *[self.pool[url] for url in library])
		
	def _add(self, mission):
		if mission.url not in self.pool:
			self.add_child(mission)
			self.pool[mission.url] = mission
			
	def add(self, pool_name, **missions):
		pool = getattr(self, pool_name)
		
		for mission in missions:
			self._add(mission)
			pool[mission.url] = mission
			
		self.bubble("MISSION_LIST_REARRANGED", pool)
			
	def remove(self, pool_name, **missions):
		pool = getattr(self, pool_name)
		
		# check mission state
		for mission in missions:
			if mission.state in ("ANALYZING", "DOWNLOADING"):
				raise Exception("Mission in use")
		
		for mission in missions:
			del pool[mission.url]
			if mission.url not in self.view and mission.url not in self.library:
				del self.pool[mission.url]

		self.bubble("MISSION_LIST_REARRANGED", pool)
		
	def contains(self, mission, pool_name=None):
		"""Check if mission in pool"""
		return self.contains_url(mission.url)
	
	def contains_url(self, url, pool_name=None):
		if pool_name is None:
			return url in self.pool
			
		return url in getattr(self, pool_name)
		
	def is_empty(self, pool_name=None):
		if pool_name is None:
			return len(self.pool)
		return len(getattr(self, pool_name))
		
	def lift(self, pool_name, **missions):
		"""Lift missions"""
		pass
		
	def drop(self, pool_name, **missions):
		pass
		
	def get_by_state(self, pool_name, states):
		for mission in getattr(self, pool_name).values():
			if mission.state in states:
				return mission
				
	def get_by_url(self, url, pool_name=None):
		if not pool_name:
			return self.pool[url]
		return getattr(self, pool_name)[url]
		
	def clean_finished(self):
		s = []
		for mission in self.view.values():
			if mission.state == "FINISHED":
				s.append(mission)
		self.remove("view", *s)

class DownloadManager(UserWorker):
	"""DownloadManager class. Export common method."""
	
	def __init__(self):
		"""set controller"""
		super().__init__()
		
		self.mission_manager = MissionManager()
		
		self.download_thread = None
		self.analyze_threads = set()
		self.library_thread = None		
		
	def worker(self):
	
		# Message listeners
		@self.listen("DOWNLOAD_TOO_MANY_RETRY")
		def dummy(mission):
			self.mission_manager.drop("view", mission)
		
		@self.listen("DOWNLOAD_FINISHED")
		def dummy(mission, thread):
			"""After download, execute command."""
			if thread is not self.download_thread:
				return
				
			command = (
				setting.get("runafterdownload"),
				"{}/{}".format(
					setting["savepath"],
					safefilepath(thread.mission.title)
				)
			)
			
			if not command[0]:
				return
				
			try:
				subprocess.call(command)
			except Exception as er:
				safeprint("Failed to run process: {}\n{}".format(command, traceback.format_exc()))
						
		@self.listen("DOWNLOAD_FINISHED")
		@self.listen("DOWNLOAD_ERROR")
		def dummy(mission, thread):
			"""After download, continue next mission"""
			if thread is self.download_thread:
				mission = self.get_mission_to_download()
				if mission:
					worker = self.create_child(download, mission, setting["savepath"])
					worker.start()
					self.downloadWorker = worker
				else:
					safeprint("All download completed")
				
		@self.listen("ANALYZE_FAILED")
		@self.listen("ANALYZE_FINISHED")
		def dummy(mission, thread):
			"""After analyze, continue next (library)"""
			if thread is self.library_thread:
				if mission.state == "UPDATE":
					self.mission_manager.lift("library", mission)
					
				mission = self.get_mission_to_check_update()
				if mission:
					self.library_thread = self.create_child(analyze).start(mission)
					
		@self.listen("ANALYZE_FINISHED")
		def dummy(mission, thread):
			if thread in self.analyze_threads:
				self.analyze_threads.remove(thread)
				self.bubble("AFTER_ANALYZE", mission)
					
		@self.listen("ANALYZE_FAILED")
		def dummy(mission, thread):
			if thread in self.analyze_threads:
				self.analyze_threads.remove(thread)
				self.bubble("AFTER_ANALYZE_FAILED", mission)
					
		self.prepare_config()
					
		if setting.getboolean("libraryautocheck"):
			self.start_check_update()

		self.message_loop()
		
	def get_mission_to_download(self):
		states = ("ANALYZED", "PAUSE", "ERROR")
		return self.mission_manager.get_by_state("view", states)
		
	def get_mission_to_check_update(self):
		states = ("ANALYZE_INIT",)
		return self.mission_manager.get_by_state("library", states)
			
	def prepare_config(self):
		"""Load config from controller. Set default"""
		default = {
			"savepath": "download",
			"runafterdownload": "",
			"libraryautocheck": "True"
		}
		
		section("DEFAULT", default)
		
		setting["savepath"] = path.normpath(setting["savepath"])
		
	def add_url(self, url):
		"""add url"""
		if not url:
			return
			
		try:
			mission = self.mission_manager.get_by_url(url, "library")
			
		except KeyError:
			mission = Mission(url=url)
			# Add to mission manager AFTER analyze
			# self.mission_manager.add("view", mission)
			
		self.analyze_threads.add(self.create_child(analyze).start(mission))
		
	def start_download(self):
		"""Start downloading"""
		if self.download_thread and self.download_thread.is_running():
			return
			
		mission = get_mission_to_download()
		if not mission:
			safeprint("所有任務已下載完成")
			return
			
		safeprint("Start download " + mission.title)
		self.download_thread = self.create_child(download).start(mission, setting["savepath"])
		
	def stop_download(self):
		"""Stop downloading"""
		if self.download_thread:
			self.download_thread.stop()
			safeprint("Stop downloading")
		
	def start_check_update(self):
		"""Start check library update"""
		if self.library_thread and self.library_thread.is_running():
			return
			
		for mission in self.mission_manager.library.values():
			mission.set("state", "ANALYZE_INIT")
			
		mission = self.get_mission_to_check_update()
		if mission:
			self.library_thread = self.create_child(analyze).start(mission)
		
	def add_mission_update(self):
		"""Add updated mission to download list"""
		missions = [mission for mission in self.mission_manager.library.values() if mission.state == "UPDATE"]
		self.mission_manager.add("view", *missions)
		
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
