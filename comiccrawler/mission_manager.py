#! python3

"""Mission Manager"""

import json
import hashlib

from collections import OrderedDict
from threading import Lock
from contextlib import suppress, contextmanager

from worker import current

from .safeprint import print
from .core import Mission, Episode, MissionProxy, safefilepath, mission_lock
from .io import backup, open, remove, move
from .profile import get as profile
from .channel import mission_ch

def get_mission_id(mission):
	"""Use title and sha1 of URL as mission id"""
	return "{title} [{sha1}]".format(
		title=mission.title,
		sha1=hashlib.sha1(mission.url.encode("utf-8")).hexdigest()[:6]
	)
	
@contextmanager
def edit_mission_id(mission):
	"""A contextmanager for changing mission title."""
	old_id = get_mission_id(mission)
	yield
	new_id = get_mission_id(mission)
	
	if old_id == new_id:
		return
	
	old_path = make_ep_path(old_id)
	new_path = make_ep_path(new_id)
	
	move(old_path, new_path)
	
def make_ep_path(id):
	"""Construct ep path with id"""
	return profile("pool/" + safefilepath(id + ".json"))
	
def get_ep_path(mission):
	"""Return episode save file path"""
	return make_ep_path(get_mission_id(mission))
	
load_episodes_status = {}
load_episodes_lock = Lock()

@contextmanager
def load_episodes(mission):
	mission_id = id(mission)
	with load_episodes_lock:
		if not mission.episodes:
			eps = load(get_ep_path(mission))
			if eps:
				mission.episodes = [Episode(**e) for e in eps]
		if mission_id in load_episodes_status:
			load_episodes_status[mission_id] += 1
		else:
			load_episodes_status[mission_id] = 1
	try:
		yield
	finally:
		with load_episodes_lock:
			if mission.episodes and load_episodes_status[mission_id] == 1:
				file = get_ep_path(mission)
				dump(mission.episodes, file)
				mission.episodes = None
				del load_episodes_status[mission_id]
			else:
				load_episodes_status[mission_id] -= 1

def cleanup_episode(mission):
	"""Remove episode save file. (probably because the mission is removed from
	the mission manager)
	"""
	remove(get_ep_path(mission))
		
def load(file):
	"""My json.load"""
	with suppress(OSError):
		with open(file) as fp:
			return json.load(fp)
				
def dump(data, file):
	"""My json.dump"""
	
	def encoder(object):
		"""Encode any object to json."""
		if hasattr(object, "tojson"):
			return object.tojson()
		return vars(object)
		
	with open(file, "w") as fp:
		json.dump(
			data,
			fp,
			indent=4,
			ensure_ascii=False,
			default=encoder
		)

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
			dump(list(self.pool.values()), profile("pool.json"))
			dump(list(self.view), profile("view.json"))
			dump(list(self.library), profile("library.json"))
			
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
		pool = load(profile("pool.json")) or []
		view = load(profile("view.json")) or []
		library = load(profile("library.json")) or []

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
			mission = MissionProxy(Mission(**m_data))
			
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

	def get_by_state(self, pool_name, states):
		"""Get first mission matching states."""
		with self.lock:
			for mission in getattr(self, pool_name).values():
				if mission.state in states:
					return mission
			return None
			
	def get_all_by_state(self, pool_name, states):
		"""Get all missions matching states"""
		with self.lock:
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
