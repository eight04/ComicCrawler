#! python3

"""Download Manager"""

from collections import deque, defaultdict
import re
import subprocess # nosec
import shlex
import sys
import traceback
from threading import Lock
from types import ModuleType

from os.path import join as path_join
from time import time

from worker import Worker, current, await_, create_worker, async_
from bidict import bidict

from .analyzer import Analyzer
from .safeprint import print
from .batch_analyzer import BatchAnalyzer
from .config import setting
from .mission import create_mission
from .crawler import download
from .profile import get as profile
from .error import PauseDownloadError
from .util import safefilepath
from .logger import debug_log

from .mission_manager import mission_manager
from .channel import download_ch
from .episode_loader import load_episodes

def quote(item):
	if sys.platform == "win32":
		return subprocess.list2cmdline([item])
	return shlex.quote(item)
	
class ThreadSafeSet:
	def __init__(self):
		self.lock = Lock()
		self.obj = set()
		
	def add(self, item):
		with self.lock:
			return self.obj.add(item)
			
	def remove(self, item):
		with self.lock:
			return self.obj.remove(item)
			
	def copy(self):
		with self.lock:
			return self.obj.copy()

class DownloadManager:
	"""Create a download manager used in GUI. Manage threads."""

	def __init__(self):
		"""Construct."""
		self.lock = Lock()
		self.crawlers: bidict[ModuleType, Worker] = bidict()
		self.mod_errors: dict[ModuleType, int] = defaultdict(int)
		self.analyze_threads = ThreadSafeSet()
		self.library_thread = None
		self.library_err_count = None
		self.batch_analyzer = None

		thread = current()
		self.thread = thread
		
		download_ch.sub(thread)

		@thread.listen("DOWNLOAD_ERROR")
		def _(event):
			_err, mission = event.data
			mission_manager.drop("view", mission)
			self.mod_errors[mission.module] += 1

		@thread.listen("DOWNLOAD_FINISHED")
		def _(event):
			"""After download, execute command."""
			with self.lock:
				if event.target not in self.crawlers.values():
					return
				self.mod_errors[event.data.module] = 0
				
			cmd = event.data.module.config.get("runafterdownload")
			default_cmd = setting.get("runafterdownload")
			
			commands = []
			
			if cmd:
				commands.append(cmd)
				
			if default_cmd and default_cmd not in commands:
				commands.append(default_cmd)
			
			def run_command():
				for command in commands:
					target = quote(path_join(
						profile(event.data.module.config["savepath"]),
						safefilepath(event.data.title)
					))
					if "{target}" in command:
						command = command.format(target=target)
					else:
						command += " " + target
					print(f"run command: {command}")
					try:
						await_(subprocess.call, command, shell=True) # nosec
					except (OSError, subprocess.SubprocessError):
						traceback.print_exc()

			async_(run_command)
						
		@thread.listen("DOWNLOAD_FINISHED")
		@thread.listen("DOWNLOAD_ERROR")
		def _(event):
			"""After download, continue next mission"""
			with self.lock:
				mod = self.crawlers.inverse.pop(event.target, None)
				if not mod:
					return

			max_errors = int(mod.config.get("max_errors", 3))
			if self.mod_errors[mod] >= max_errors:
				print(f"{mod.name} 失敗 {max_errors} 次，停止下載")
				self.mod_errors[mod] = 0
				return

			self.start_download_mod(mod)

		@thread.listen("DOWNLOAD_INVALID")
		def _(event):
			"""Something bad happened"""
			with self.lock:
				mod = self.crawlers.inverse.pop(event.target, None)
				if mod:
					print(f"{mod.name} 停止下載")

	def start_download(self):
		"""Start downloading."""
		self.start_download_all()

	def start_download_all(self):
		missions = mission_manager.get_all("view", lambda m: m.state in ("ANALYZED", "PAUSE", "ERROR", "UPDATE"))
		if not missions:
			print("所有任務已下載完成")
			return

		for mission in missions:
			self.start_download_mod(mission.module)

	def start_download_mod(self, mod):
		"""Start downloading from a specific mod."""
		mission = mission_manager.get("view", lambda m: m.module == mod and m.state in ("ANALYZED", "PAUSE", "ERROR", "UPDATE"))
		if not mission:
			return

		with self.lock:
			if mod in self.crawlers:
				return

			def do_download():
				debug_log("do_download")
				with load_episodes(mission):
					download(mission, profile(mission.module.config["savepath"]))

			self.crawlers[mod] = Worker(do_download).start()

	def stop_download(self):
		"""Stop downloading."""
		with self.lock:
			if not self.crawlers:
				return

			for crawler in self.crawlers.values():
				crawler.stop()

			# FIXME: shouldn't we wait for thread stop?
			self.crawlers.clear()
			print("Stop downloading")
			
	def start_analyze(self, mission, on_finished=None):
		"""Start analyzing"""
		if mission.state not in ("ANALYZE_INIT", "INIT"):
			print(
				"Invalid state to analyze: {state}".format(state=mission.state))
			return
			
		@create_worker
		def analyze_thread():
			err = None
			with load_episodes(mission):
				try:
					Analyzer(mission).analyze()
				except BaseException as _err:
					err = _err
					raise
				else:
					mission_manager.add("view", mission)
				finally:
					if on_finished:
						on_finished(err)
					self.analyze_threads.remove(analyze_thread)
		self.analyze_threads.add(analyze_thread)
		
	def start_batch_analyze(self, missions):
		"""Start batch analyze"""
		if self.batch_analyzer:
			print("Batch analyzer is already running")
			return
			
		if isinstance(missions, str):
			missions = [
				create_mission(url=m) for m in re.split(r"\s+", missions) if m]
		missions = deque(missions)
				
		def gen_missions():
			while missions:
				yield missions[0]
				
		def on_item_finished(err, mission):
			if not err:
				missions.popleft()
				mission_manager.add("view", mission)
				download_ch.pub("BATCH_ANALYZE_UPDATE", list(missions))
			
		def on_finished(err):
			self.batch_analyzer = None
			download_ch.pub("BATCH_ANALYZE_END", err)
			
		self.batch_analyzer = BatchAnalyzer(
			gen_missions=gen_missions(),
			on_item_finished=on_item_finished,
			on_finished=on_finished
		)
		self.batch_analyzer.start()
		
	def stop_batch_analyze(self):
		"""Stop batch analyzer"""
		if not self.batch_analyzer:
			print("No batch analyzer exists")
			return
			
		self.batch_analyzer.stop()
		
	def stop_analyze(self):
		"""Stop analyze"""
		for thread in self.analyze_threads.copy():
			thread.stop()
			self.analyze_threads.remove(thread)

	def start_check_update(self, missions=None):
		"""Start checking library update."""
		if self.library_thread:
			print("Already checking update")
			return
			
		# set mission state to ANALYZE_INIT
		setting["lastcheckupdate"] = str(time())
		
		if missions is None:
			missions = mission_manager.get_all("library", lambda m: m.state not in ("DOWNLOADING", "ANALYZING"))
			
		for mission in missions:
			mission.state = "ANALYZE_INIT"
			
		missions = set(missions)
				
		def gen_missions():
			while True:
				mission = mission_manager.get("library", lambda m: m.state in ("ANALYZE_INIT", "ERROR") and m in missions)
				if not mission:
					return
				yield mission
				
		self.library_err_count = 0
		def on_item_finished(err, mission):
			if err:
				traceback.print_exception(err)
			if mission.state == "UPDATE":
				mission_manager.lift("library", mission)
			elif mission.state == "ERROR":
				mission_manager.drop("library", mission)
				self.library_err_count += 1
				
		def stop_on_error(err):
			return self.library_err_count > 10 or isinstance(err, PauseDownloadError)
				
		def on_finished(err):
			self.library_thread = None
			if err:
				download_ch.pub("LIBRARY_CHECK_UPDATE_FAILED", err)
				print("Failed to check update")
			else:
				print("Update checking done")
				
		self.library_thread = BatchAnalyzer(
			gen_missions=gen_missions(),
			on_item_finished=on_item_finished,
			on_finished=on_finished,
			stop_on_error=stop_on_error
		)
		self.library_thread.start()
	
	def stop_check_update(self):
		"""Stop checking update"""
		if self.library_thread:
			self.library_thread.stop()
			self.library_thread = None

	def is_downloading(self):
		with self.lock:
			return bool(self.crawlers)
		
download_manager = DownloadManager()
