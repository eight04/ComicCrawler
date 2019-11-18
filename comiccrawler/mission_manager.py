#! python3

"""Mission Manager"""

from collections import OrderedDict
from threading import Lock

from worker import current

from .safeprint import print
from .mission import create_mission, mission_lock
from .episode import Episode
from .io import backup, json_load, json_dump
from .profile import get as profile
from .channel import mission_ch
from .episode_loader import cleanup_episode

class MissionManager:
	"""Since check_update thread might grab mission from mission_manager, we
	have to make it thread safe.
	"""
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
			cleanup_episode(self.pool[url])
			del self.pool[url]

	def save(self):
		"""Save missions to json."""
		if not self.edit:
			return

		with mission_lock:
			json_dump(list(self.pool.values()), profile("pool.json"))
			json_dump(list(self.view), profile("view.json"))
			json_dump(list(self.library), profile("library.json"))
			
		self.edit = False
		print("Session saved")

	def load(self):
		"""Load mission from json.

		If failing to load missions, create json backup .
		"""
		try:
			self._load()
		except Exception:
			print("Failed to load session!")
			backup(profile("*.json"))
			raise
		self.cleanup()

	def _load(self):
		"""Load missions from json. Called by MissionManager.load."""
		pool = json_load(profile("pool.json")) or []
		view = json_load(profile("view.json")) or []
		library = json_load(profile("library.json")) or []

		for m_data in pool:
			# reset state
			if m_data["state"] in ("DOWNLOADING", "ANALYZING"):
				m_data["state"] = "ERROR"
			# build episodes
			# compatible 2016.6.4
			if m_data["episodes"]:
				episodes = []
				for ep_data in m_data["episodes"]:
					# compatible 2016.4.3
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
			mission = create_mission(**m_data)
			
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
				if mission.url in pool:
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
		
	def sort(self, pool_name, key, reverse=False):
		pool = getattr(self, pool_name)
		with self.lock:
			for mission in sorted(pool.values(), key=key):
				pool.move_to_end(mission.url, last=not reverse)
		mission_ch.pub("MISSION_LIST_REARRANGED", pool)
		self.edit = True
		
	def get_all(self, pool_name, test=None):
		"""Get all missions matching condition."""
		with self.lock:
			return [m for m in getattr(self, pool_name).values() if not test or test(m)]
			
	def get(self, pool_name, test=None):
		"""Get the first mission matching condition."""
		with self.lock:
			for mission in getattr(self, pool_name).values():
				if not test or test(mission):
					return mission

	def get_by_url(self, url, pool_name=None):
		"""Get mission by url."""
		if not pool_name:
			return self.pool[url]
		return getattr(self, pool_name)[url]

mission_manager = MissionManager()
