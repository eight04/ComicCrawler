#! python3

"""Download Manager"""

import re
import subprocess # nosec
import shlex
import sys
import traceback

from os.path import join as path_join
from time import time

from worker import Worker, current, later, await_

from .safeprint import print
from .config import setting
from .core import download, analyze, safefilepath, BatchAnalyzer, create_mission
from .profile import get as profile

from .mission_manager import mission_manager, init_episode, uninit_episode
from .channel import download_ch

def quote(item):
	if sys.platform == "win32":
		return subprocess.list2cmdline([item])
	return shlex.quote(item)

class DownloadManager:
	"""Create a download manager used in GUI. Manage threads."""

	def __init__(self):
		"""Construct."""
		self.download_thread = None
		self.analyze_threads = set()
		self.library_thread = None
		self.library_err_count = None
		self.library_cooldown_timestamp = {}
		self.batch_analyzer = None
		
		thread = current()
		
		download_ch.sub(thread)
		
		@thread.listen("DOWNLOAD_PAUSE")
		@thread.listen("DOWNLOAD_INVALID")
		@thread.listen("DOWNLOAD_ERROR")
		@thread.listen("DOWNLOAD_FINISHED")
		def _(event):
			try:
				_err, mission = event.data
			except TypeError:
				mission = event.data

			if mission.url in mission_manager.pool:
				uninit_episode(mission)
		
		@thread.listen("DOWNLOAD_ERROR")
		def _(event):
			_err, mission = event.data
			mission_manager.drop("view", mission)

		@thread.listen("DOWNLOAD_FINISHED")
		def _(event):
			"""After download, execute command."""
			if event.target is not self.download_thread:
				return
				
			cmd = event.data.module.config.get("runafterdownload")
			default_cmd = setting.get("runafterdownload")
			
			commands = []
			
			if cmd:
				commands.append(cmd)
				
			if default_cmd and default_cmd not in commands:
				commands.append(default_cmd)
			
			for command in commands:
				command += " " + quote(path_join(
					profile(event.data.module.config["savepath"]),
					safefilepath(event.data.title)
				))
				try:
					await_(subprocess.call, command, shell=True) # nosec
				except (OSError, subprocess.SubprocessError):
					traceback.print_exc()
					
		@thread.listen("DOWNLOAD_FINISHED")
		@thread.listen("DOWNLOAD_ERROR")
		def _(event):
			"""After download, continue next mission"""
			if event.target is self.download_thread:
				self.download_thread = None
				self.start_download()
				
		@thread.listen("DOWNLOAD_INVALID")
		def _(event):
			"""Something bad happened"""
			if event.target is self.download_thread:
				self.download_thread = None
				print("停止下載")

		@thread.listen("ANALYZE_FAILED")
		@thread.listen("ANALYZE_FINISHED")
		def _(event):
			"""After analyze, continue next (library)"""
			try:
				_err, mission = event.data
			except TypeError:
				mission = event.data
				
			self.library_cooldown_timestamp[mission.module.name] = time()
				
			if event.target is self.library_thread:
				uninit_episode(mission)
				if mission.state == "UPDATE":
					mission_manager.lift("library", mission)
					
				if mission.state == "ERROR":
					if self.library_err_count > 10:
						print("Too many error!")
						download_ch.pub("LIBRARY_CHECK_UPDATE_FAILED")
						self.library_thread = None
					else:
						self.library_err_count += 1
						mission_manager.drop("library", mission)
						later(self.do_check_update, 5, target=thread)
					return
					
				self.do_check_update()
				
		@thread.listen("ANALYZE_INVALID")
		def _(event):
			"""Cleanup library thread with PauseDownloadError"""
			_err, mission = event.data
			if event.target is self.library_thread:
				uninit_episode(mission)
				self.library_thread = None
				print("Failed to check update")

		@thread.listen("ANALYZE_FINISHED")
		def _(event):
			"""After analyze, add to view (view analyzer)"""
			if event.target in self.analyze_threads:
				mission = event.data
				uninit_episode(mission)
				mission_manager.add("view", mission)
				download_ch.pub("ANALYZE_NEW_MISSION", mission)

		@thread.listen("ANALYZE_FINISHED")
		@thread.listen("ANALYZE_FAILED")
		def _(event):
			if event.target in self.analyze_threads:
				self.analyze_threads.remove(event.target)
				
		@thread.listen("BATCH_ANALYZE_END")
		def _(event):
			self.batch_analyzer = None
			
		@thread.listen("BATCH_ANALYZE_ITEM_FINISHED")
		def _(event):
			_analyzer, mission = event.data
			mission_manager.add("view", mission)

	def start_download(self):
		"""Start downloading."""
		if self.download_thread:
			return

		mission = mission_manager.get_by_state("view", ("ANALYZED", "PAUSE", "ERROR", "UPDATE"))
		if mission:
			print("Start download " + mission.title)
			init_episode(mission)
			self.download_thread = Worker(download).start(
				mission,
				profile(mission.module.config["savepath"])
			)
		else:
			print("所有任務已下載完成")

	def stop_download(self):
		"""Stop downloading."""
		if self.download_thread:
			self.download_thread.stop()
			self.download_thread = None
			print("Stop downloading")
			
	def start_analyze(self, mission):
		"""Start analyzing"""
		if mission.state not in ("ANALYZE_INIT", "INIT"):
			print(
				"Invalid state to analyze: {state}".format(state=mission.state))
			return
		init_episode(mission)
		thread = Worker(analyze).start(mission)
		self.analyze_threads.add(thread)
		
	def start_batch_analyze(self, missions):
		"""Start batch analyze"""
		if self.batch_analyzer:
			print("There is already a working batch analyzer")
			return
			
		if isinstance(missions, str):
			missions = [
				create_mission(m) for m in re.split("\s+", missions) if m]
			
		self.batch_analyzer = BatchAnalyzer(missions).start()
		
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

	def start_check_update(self):
		"""Start checking library update."""
		if self.library_thread:
			print("Already checking update")
			return

		self.library_err_count = 0
		setting["lastcheckupdate"] = str(time())
		for mission in mission_manager.library.values():
			if mission.state not in ("DOWNLOADING", "ANALYZING"):
				mission.state = "ANALYZE_INIT"
				
		self.do_check_update()
	
	def do_check_update(self):
		"""Check library update"""
		mission = mission_manager.get_by_state("library", ("ANALYZE_INIT", "ERROR"))
		if mission:
			init_episode(mission)
			self.library_thread = later(
				analyze,
				get_analyze_cooldown(self.library_cooldown_timestamp, mission),
				mission
			)
		else:
			self.library_thread = None
			print("Update checking done")
			
	def stop_check_update(self):
		"""Stop checking update"""
		if self.library_thread:
			self.library_thread.stop()
			self.library_thread = None

	def is_downloading(self):
		return self.download_thread is not None
		
def get_analyze_cooldown(map, mission):
	if not hasattr(mission.module, "rest_analyze"):
		return 0
	pre_ts = map.get(mission.module.name)
	if pre_ts is None:
		return 0
	cooldown = mission.module.rest_analyze - (time() - pre_ts)
	return cooldown if cooldown > 0 else 0
		
download_manager = DownloadManager()
