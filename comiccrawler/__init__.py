#! python3

"""Comic Crawler

Usage:
  comiccrawler domains
  comiccrawler download URL [--dest SAVE_FOLDER]
  comiccrawler gui
  comiccrawler migrate
  comiccrawler (--help | --version)

Commands:
  domains             List supported domains.
  download URL        Download from the URL.
  gui                 Launch TKinter GUI.
  migrate             Migrate from old version, convert save file to new
                      format.

Options:
  --dest SAVE_FOLDER  Set download save path. [default: .]
  --help              Show help message.
  --version           Show current version.

Sub modules:
  comiccrawler.core   Core functions of downloading, analyzing.
  comiccrawler.error  Errors.
  comiccrawler.mods   Import download modules.
"""

__version__ = "2015.7.7"

import subprocess, traceback, json

from worker import Worker, UserWorker, WorkerExit
from os import path
from collections import OrderedDict

from .safeprint import safeprint
from .config import setting, section
from .core import Mission, Episode, download, analyze, safefilepath
from .io import content_read, content_write, is_file
from .mods import list_domain, load_config

from . import config, io

from .mission_manager import MissionManager

class DownloadManager(UserWorker):
	"""Create a download manager used in GUI."""

	def __init__(self):
		"""Construct."""
		super().__init__()

		self.mission_manager = self.create_child(MissionManager)

		self.download_thread = None
		self.analyze_threads = set()
		self.library_thread = None

	def worker(self):
		"""Override."""
		@self.listen("DOWNLOAD_ERROR")
		def dummy(mission):
			self.mission_manager.drop("view", mission)

		@self.listen("DOWNLOAD_FINISHED")
		def dummy(mission, thread):
			"""After download, execute command."""
			if thread is not self.download_thread:
				return

			command = (
				setting.get("runafterdownload"),
				path.join(
					setting["savepath"],
					safefilepath(mission.title)
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
					worker = self.create_child(download)
					worker.start(mission, setting["savepath"])
					self.download_thread = worker
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

		self.reload_config()
		self.mission_manager.start()

		if setting.getboolean("libraryautocheck"):
			self.start_check_update()

		self.message_loop()

	def get_mission_to_download(self):
		"""Select those missions which available to download."""
		states = ("ANALYZED", "PAUSE", "ERROR")
		return self.mission_manager.get_by_state("view", states)

	def get_mission_to_check_update(self):
		"""Select those missions which available to check update."""
		states = ("ANALYZE_INIT",)
		return self.mission_manager.get_by_state("library", states)

	def reload_config(self):
		"""Load config from setting.ini and call mods.load_config."""
		config.load("~/comiccrawler/setting.ini")

		default = {
			"savepath": "~/comiccrawler/download",
			"runafterdownload": "",
			"libraryautocheck": "True"
		}

		section("DEFAULT", default)

		setting["savepath"] = path.normpath(setting["savepath"])

		load_config()

	def create_mission(self, url):
		"""Create the mission from url."""
		return Mission(url=url)

	def start_analyze(self, mission):
		"""Analyze the mission."""
		thread = self.create_child(analyze)
		self.analyze_threads.add(thread)
		thread.start(mission)

	def start_download(self):
		"""Start downloading."""
		if self.download_thread and self.download_thread.is_running():
			return

		mission = self.get_mission_to_download()
		if not mission:
			safeprint("所有任務已下載完成")
			return

		safeprint("Start download " + mission.title)
		self.download_thread = self.create_child(download).start(mission, setting["savepath"])

	def stop_download(self):
		"""Stop downloading."""
		if self.download_thread:
			self.download_thread.stop()
			safeprint("Stop downloading")

	def start_check_update(self):
		"""Start checking library update."""
		if self.library_thread and self.library_thread.is_running():
			return

		for mission in self.mission_manager.library.values():
			mission.set("state", "ANALYZE_INIT")

		mission = self.get_mission_to_check_update()
		if mission:
			self.library_thread = self.create_child(analyze).start(mission)

	def add_mission_update(self):
		"""Add updated mission to download list."""
		missions = self.mission_manager.get_by_state(
			"library", ("UPDATE",), all=True
		)
		self.mission_manager.add("view", *missions)

	def clean_finished(self):
		"""Remove finished missions."""
		missions = self.mission_manager.get_by_state(
			"view", ("FINISHED",), all=True
		)
		self.mission_manager.remove("view", *missions)

def console_download(url, savepath):
	"""Download url to savepath."""
	mission = Mission(url=url)
	Worker.sync(analyze, mission, pass_instance=True)
	Worker.sync(download, mission, savepath, pass_instance=True)

def console_init():
	"""Console init."""
	from docopt import docopt

	arguments = docopt(__doc__, version="Comic Crawler v" + __version__)

	if arguments["domains"]:
		print("Supported domains:\n" + ", ".join(list_domain()))

	elif arguments["gui"]:
		from .gui import MainWindow
		MainWindow().run()

	elif arguments["download"]:
		console_download(arguments["URL"], arguments["savepath"])

	elif arguments["migrate"]:
		from .migrate import migrate
		migrate()
