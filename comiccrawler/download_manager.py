#! python3

"""Download Manager"""

from collections import deque
import re
import subprocess # nosec
import shlex
import sys
import traceback

from os.path import join as path_join
from time import time

from worker import Worker, current, await_

from .analyzer import analyze
from .safeprint import print
from .batch_analyzer import BatchAnalyzer
from .config import setting
from .mission import create_mission
from .crawler import download
from .profile import get as profile
from .error import PauseDownloadError
from .util import safefilepath

from .mission_manager import mission_manager
from .channel import download_ch
from .episode_loader import load_episodes

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

		@thread.listen("ANALYZE_FINISHED")
		def _(event):
			"""After analyze, add to view (view analyzer)"""
			if event.target in self.analyze_threads:
				mission = event.data
				mission_manager.add("view", mission)
				download_ch.pub("ANALYZE_NEW_MISSION", mission)

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
			def do_download():
				with load_episodes(mission):
					download(mission, profile(mission.module.config["savepath"]))
			self.download_thread = Worker(do_download).start()
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
		def do_analyze():
			with load_episodes(mission):
				analyze(mission)
		thread = Worker(do_analyze).start()
		self.analyze_threads.add(thread)
		
	def start_batch_analyze(self, missions):
		"""Start batch analyze"""
		if self.batch_analyzer:
			print("Batch analyzer is already running")
			return
			
		if isinstance(missions, str):
			missions = [
				create_mission(url=m) for m in re.split("\s+", missions) if m]
		missions = deque(missions)
				
		def gen_missions():
			while missions:
				yield missions[0]
				
		def done_item(err, mission):
			if not err:
				missions.popleft()
				mission_manager.add("view", mission)
				download_ch.pub("BATCH_ANALYZE_UPDATE", list(missions))
			
		def done(err):
			self.batch_analyzer = None
			download_ch.pub("BATCH_ANALYZE_END", err)
			
		self.batch_analyzer = BatchAnalyzer(
			gen_missions=gen_missions(),
			done_item=done_item,
			done=done
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

	def start_check_update(self):
		"""Start checking library update."""
		if self.library_thread:
			print("Already checking update")
			return
			
		# set mission state to ANALYZE_INIT
		setting["lastcheckupdate"] = str(time())
		for mission in mission_manager.library.values():
			if mission.state not in ("DOWNLOADING", "ANALYZING"):
				mission.state = "ANALYZE_INIT"
				
		def gen_missions():
			while True:
				mission = mission_manager.get_by_state("library", ("ANALYZE_INIT", "ERROR"))
				if not mission:
					return
				yield mission
				
		self.library_err_count = 0
		def done_item(err, mission):
			if mission.state == "UPDATE":
				mission_manager.lift("library", mission)
			elif mission.state == "ERROR":
				mission_manager.drop("library", mission)
				self.library_err_count += 1
				
		def stop_on_error(err):
			return self.library_err_count > 10 or isinstance(err, PauseDownloadError)
				
		def done(err):
			self.library_thread = None
			if err:
				if self.library_err_count > 10:
					download_ch.pub("LIBRARY_CHECK_UPDATE_FAILED")
				print("Failed to check update")
			else:
				print("Update checking done")
				
		self.library_thread = BatchAnalyzer(
			gen_missions=gen_missions(),
			done_item=done_item,
			done=done,
			stop_on_error=stop_on_error
		)
		self.library_thread.start()
	
	def stop_check_update(self):
		"""Stop checking update"""
		if self.library_thread:
			self.library_thread.stop()
			self.library_thread = None

	def is_downloading(self):
		return self.download_thread is not None
		
download_manager = DownloadManager()
