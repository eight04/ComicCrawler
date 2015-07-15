#! python3

"""Mission Manager"""

import json, traceback, worker
from os import path
from collections import OrderedDict

from .safeprint import safeprint
from .config import setting
from .core import Mission, Episode
from .io import content_read, content_write, is_file, move

def shallow(dict, exclude=None):
	"""Return a shallow copy of a dict.

	Arguments:
	exclude - A list of key name which should not to copy. (default: None)
	"""
	new_dict = {}
	for key in dict:
		if not exclude or key not in exclude:
			new_dict[key] = dict[key]
	return new_dict

class MissionPoolEncoder(json.JSONEncoder):
	"""Encode Mission, Episode to json."""

	def default(self, object):
		if isinstance(object, Mission):
			return shallow(vars(object), exclude=["module", "thread"])

		if isinstance(object, Episode):
			return shallow(vars(object))

		return super().default(object)

class MissionManager(worker.UserWorker):
	"""Save, load missions from files"""

	def __init__(self):
		"""Construct."""
		super().__init__()

		self.pool = {}
		self.view = OrderedDict()
		self.library = OrderedDict()
		self.edit = False

	def worker(self):
		"""Override. The worker target."""
		@self.listen("MISSION_PROPERTY_CHANGED")
		@self.listen("DOWNLOAD_EP_COMPLETE")
		def dummy():
			"""Set the edit flag after mission changed."""
			self.edit = True

		@self.listen("WORKER_DONE")
		def dummy():
			"""Save missions after the thread terminate."""
			self.save()

		self.load()
		while True:
			self.wait(setting.getint("autosave", 5) * 60)
			self.save()

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
		safeprint("Session saved")

	def load(self):
		"""Load mission from json.

		If it fail to load missions, create json backup in
		`~/comiccrawler/invalid-save`.
		"""
		try:
			self._load()
		except Exception:
			import time
			dest = path.join(
				"~/comiccrawler/invalid-save",
				time.strftime("%Y-%m-%d %H.%M.%S")
			)

			exc = traceback.format_exc()

			safeprint("Can't read save files! Move files to {}\n\n{}".format(
				dest,
				exc
			))

			move(
				"~/comiccrawler/*.json",
				dest
			)

			self.bubble("MISSION_POOL_LOAD_FAILED", (dest, exc))

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
				episodes.append(Episode(**ep_data))
			m_data["episodes"] = episodes
			mission = Mission(**m_data)
			self._add(mission)

		self.add("view", *[self.pool[url] for url in view])
		self.add("library", *[self.pool[url] for url in library])

	def _add(self, mission):
		"""Add mission to public pool."""
		if mission.url not in self.pool:
			self.add_child(mission)
			self.pool[mission.url] = mission

	def add(self, pool_name, *missions):
		"""Add missions to pool."""
		pool = getattr(self, pool_name)

		for mission in missions:
			self._add(mission)
			pool[mission.url] = mission

		self.bubble("MISSION_LIST_REARRANGED", pool)
		self.edit = True

	def remove(self, pool_name, *missions):
		"""Remove missions from pool."""
		pool = getattr(self, pool_name)

		# check mission state
		missions = [m for m in missions if m.state not in ("ANALYZING", "DOWNLOADING")]

		for mission in missions:
			del pool[mission.url]
			if mission.url not in self.view and mission.url not in self.library:
				del self.pool[mission.url]

		self.bubble("MISSION_LIST_REARRANGED", pool)
		self.edit = True

	def lift(self, pool_name, *missions):
		"""Lift missions to the top."""
		pool = getattr(self, pool_name)
		for mission in reversed(missions):
			pool.move_to_end(mission.url, last=False)
		self.bubble("MISSION_LIST_REARRANGED", pool)
		self.edit = True

	def drop(self, pool_name, *missions):
		"""Drop missions to the bottom."""
		pool = getattr(self, pool_name)
		for mission in missions:
			pool.move_to_end(mission.url)
		self.bubble("MISSION_LIST_REARRANGED", pool)
		self.edit = True

	def get_by_state(self, pool_name, states, all=False):
		"""Get missions by states."""
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

