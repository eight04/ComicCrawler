#! python3

"""Mission Manager"""

import json, traceback

from collections import OrderedDict
from worker import current
from threading import Lock

from .safeprint import print
from .core import Mission, Episode, MissionProxy
from .io import content_read, content_write, is_file, backup

from .channel import mission_ch

class MissionPoolEncoder(json.JSONEncoder):
	"""Encode Mission, Episode to json."""

	def default(self, object):
		if hasattr(object, "tojson"):
			return object.tojson()

		return vars(object)

class MissionManager:
	"""Since check_update thread might grab mission from mission_manager, we have to make it thread safe."""
	def __init__(self):
		"""Construct."""
		self.pool = {}
		self.view = OrderedDict()
		self.library = OrderedDict()
		self.edit = False
		self.lock = Lock()
		
		self.load()

		thread = current()
		mission_ch.sub(thread)
		@thread.listen("MISSION_PROPERTY_CHANGED")
		def _(event):
			"""Set the edit flag after mission changed."""
			self.edit = True

	def cleanup(self):
		"""Cleanup unused missions"""
		main_pool = set(self.pool)
		view_pool = set(self.view)
		library_pool = set(self.library)

		for url in main_pool - (view_pool | library_pool):
			del self.pool[url]

	def save(self):
		"""Save missions to json."""
		if not self.edit:
			return

		content_write(
			"~/comiccrawler/pool.json",
			json.dumps(
				list(self.pool.values()),
				cls=MissionPoolEncoder,
				indent=4,
				ensure_ascii=False
			)
		)
		content_write(
			"~/comiccrawler/view.json",
			json.dumps(
				list(self.view),
				indent=4,
				ensure_ascii=False
			)
		)
		content_write(
			"~/comiccrawler/library.json",
			json.dumps(
				list(self.library),
				indent=4,
				ensure_ascii=False
			)
		)
		self.edit = False
		print("Session saved")

	def load(self):
		"""Load mission from json.

		If it fail to load missions, create json backup in
		`~/comiccrawler/invalid-save`.
		"""
		try:
			self._load()
		except Exception as err:
			print("Failed to load session!")
			# traceback.print_exc()
			backup("~/comiccrawler/*.json")
			raise
			# mission_ch.pub("MISSION_POOL_LOAD_FAILED", err)
		self.cleanup()
		# mission_ch.pub("MISSION_POOL_LOAD_SUCCESS")

	def _load(self):
		"""Load missions from json. Called by MissionManager.load."""
		pool = []
		view = []
		library = []

		if is_file("~/comiccrawler/pool.json"):
			pool = json.loads(content_read("~/comiccrawler/pool.json"))

		if is_file("~/comiccrawler/view.json"):
			view = json.loads(content_read("~/comiccrawler/view.json"))

		if is_file("~/comiccrawler/library.json"):
			library = json.loads(content_read("~/comiccrawler/library.json"))

		for m_data in pool:
			# reset state
			if m_data["state"] in ("DOWNLOADING", "ANALYZING"):
				m_data["state"] = "ERROR"
			# build episodes
			episodes = []
			for ep_data in m_data["episodes"]:
				# compatible 2916.4.3
				if "total" not in ep_data:
					if not ep_data["current_url"]:
						ep_data["total"] = 0
						
					elif ep_data["url"] == ep_data["current_url"]:
						# first page crawler
						ep_data["total"] = ep_data["current_page"] - 1
						
					else:
						# per page crawler
						ep_data["total"] = ep_data["current_page"] - 1
						ep_data["current_page"] = 1
					
					if ep_data["complete"]:
						ep_data["total"] += 1
						
				episodes.append(Episode(**ep_data))
			m_data["episodes"] = episodes
			mission = MissionProxy(Mission(**m_data))
			# self._add(mission)
			self.pool[mission.url] = mission

		for url in view:
			self.view[url] = self.pool[url]

		for url in library:
			self.library[url] = self.pool[url]

		mission_ch.pub("MISSION_LIST_REARRANGED", self.view)
		mission_ch.pub("MISSION_LIST_REARRANGED", self.library)

	def add(self, pool_name, *missions):
		"""Add missions to pool."""
		pool = getattr(self, pool_name)

		with self.lock:
			for mission in missions:
				if mission.url not in self.pool:
					mission_ch.pub("MISSION_ADDED", mission)
				self.pool[mission.url] = mission					
				pool[mission.url] = mission
		
		mission_ch.pub("MISSION_LIST_REARRANGED", pool)
		self.edit = True

	def remove(self, pool_name, *missions):
		"""Remove missions from pool."""
		pool = getattr(self, pool_name)

		# check mission state
		missions = [m for m in missions if m.state not in ("ANALYZING", "DOWNLOADING")]

		with self.lock:
			for mission in missions:
				del pool[mission.url]
			self.cleanup()
			
		mission_ch.pub("MISSION_LIST_REARRANGED", pool)
		self.edit = True

	def lift(self, pool_name, *missions):
		"""Lift missions to the top."""
		pool = getattr(self, pool_name)
		with self.lock:
			for mission in reversed(missions):
				pool.move_to_end(mission.url, last=False)
		mission_ch.pub("MISSION_LIST_REARRANGED", pool)
		self.edit = True

	def drop(self, pool_name, *missions):
		"""Drop missions to the bottom."""
		pool = getattr(self, pool_name)
		with self.lock:
			for mission in missions:
				pool.move_to_end(mission.url)
		mission_ch.pub("MISSION_LIST_REARRANGED", pool)
		self.edit = True

	def get_by_state(self, pool_name, states, all=False):
		"""Get missions by states."""
		with self.lock:
			if not all:
				for mission in getattr(self, pool_name).values():
					if mission.state in states:
						return mission
				return None
			else:
				output = []
				for mission in getattr(self, pool_name).values():
					if mission.state in states:
						output.append(mission)
				return output

	def get_by_url(self, url, pool_name=None):
		"""Get mission by url."""
		if not pool_name:
			return self.pool[url]
		return getattr(self, pool_name)[url]

mission_manager = MissionManager()
