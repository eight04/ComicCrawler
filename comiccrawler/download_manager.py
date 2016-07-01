#! python3

"""Download Manager"""

import subprocess

from os.path import join as path_join
from worker import Worker, current, later
from time import time

from .safeprint import print
from .config import setting
from .core import download, analyze, safefilepath

from .mission_manager import mission_manager, init_episode, uninit_episode
from .channel import download_ch

class DownloadManager:
	"""Create a download manager used in GUI. Manage threads."""

	def __init__(self):
		"""Construct."""
		self.download_thread = None
		self.analyze_threads = set()
		self.library_thread = None
		self.library_err_count = None
		
		thread = current()
		
		download_ch.sub(thread)
		
		@thread.listen("DOWNLOAD_PAUSE")
		@thread.listen("DOWNLOAD_INVALID")
		@thread.listen("DOWNLOAD_ERROR")
		@thread.listen("DOWNLOAD_FINISHED")
		def _(event):
			try:
				err, mission = event.data
			except Exception:
				mission = event.data
			if mission.url in mission_manager.pool:
				uninit_episode(mission)
		
		@thread.listen("DOWNLOAD_ERROR")
		def _(event):
			err, mission = event.data
			mission_manager.drop("view", mission)

		@thread.listen("DOWNLOAD_FINISHED")
		def _(event):
			"""After download, execute command."""
			if event.target is not self.download_thread:
				return
				
			r1 = event.data.module.config.get("runafterdownload")
			r2 = setting.get("runafterdownload")
			
			if r1 == r2 and r1:
				commands = [r1]
			elif r1:
				commands = [r1, r2]
			else:
				commands = []
				
			for command in commands:
				command = (
					command,
					path_join(
						event.data.module.config["savepath"],
						safefilepath(event.data.title)
					)
				)
				try:
					subprocess.call(command)
				except Exception:
					print("Failed to run process: {}".format(command))
					
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
				err, mission = event.data
			except Exception:
				mission = event.data
				
			if event.target is self.library_thread:
				uninit_episode(mission)
				if mission.state == "UPDATE":
					mission_manager.lift("library", mission)
					self.do_check_update()
				elif mission.state == "ERROR":
					if self.library_err_count > 10:
						print("Too many error!")
						download_ch.pub("LIBRARY_CHECK_UPDATE_FAILED")
						return
					self.library_err_count += 1
					mission_manager.drop("library", mission)
					later(self.do_check_update, 5)
				
		@thread.listen("ANALYZE_INVALID")
		def _(event):
			"""Cleanup library thread with PauseDownloadError"""
			mission = event.data
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

		@thread.listen("ANALYZE_FINISHED")
		@thread.listen("ANALYZE_FAILED")
		def _(event):
			if event.target in self.analyze_threads:
				self.analyze_threads.remove(event.target)

	def start_download(self):
		"""Start downloading."""
		if self.download_thread:
			return

		mission = mission_manager.get_by_state("view", ("ANALYZED", "PAUSE", "ERROR", "UPDATE"))
		if mission:
			print("Start download " + mission.title)
			init_episode(mission)
			self.download_thread = Worker(download).start(mission, mission.module.config["savepath"])
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
			print("Invalid state to analyze: {state}".format(mission.state))
			return
		init_episode(mission)
		thread = Worker(analyze).start(mission)
		self.analyze_threads.add(thread)
		
	def stop_analyze(self):
		"""Stop analyze"""
		for thread in self.analyze_threads.copy():
			thread.stop()
			self.analyze_threads.remove(thread)

	def start_check_update(self):
		"""Start checking library update."""
		if self.library_thread:
			return

		self.library_err_count = 0
		for mission in mission_manager.library.values():
			if mission.state not in ("DOWNLOADING", "ANALYZING"):
				mission.state = "ANALYZE_INIT"
				
		self.do_check_update()
	
	def do_check_update(self):
		"""Check library update"""
		mission = mission_manager.get_by_state("library", ("ANALYZE_INIT", "ERROR"))
		if mission:
			init_episode(mission)
			self.library_thread = Worker(analyze).start(mission)
		else:
			self.library_thread = None
			setting["lastcheckupdate"] = str(time())
			print("Update checking done")
			
	def stop_check_update(self):
		"""Stop checking update"""
		if self.library_thread:
			self.library_thread.stop()
			self.library_thread = None

	def is_downloading(self):
		return self.download_thread is not None
		
download_manager = DownloadManager()
