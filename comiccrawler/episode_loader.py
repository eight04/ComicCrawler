import contextlib
import hashlib
import threading

from .io import json_load, json_dump, move, remove
from .util import safefilepath
from .profile import get as profile_get
from .episode import Episode
from .logger import debug_log

def get_mission_id(mission):
	"""Use title and sha1 of URL as mission id"""
	return "{title} [{sha1}]".format(
		title=mission.title,
		sha1=hashlib.sha1(mission.url.encode("utf-8")).hexdigest()[:6]
	)
	
@contextlib.contextmanager
def edit_mission_id(mission):
	"""A contextmanager for changing mission title."""
	old_id = get_mission_id(mission)
	try:
		yield
	finally:
		new_id = get_mission_id(mission)
		if old_id != new_id:
			old_path = make_ep_path(old_id)
			new_path = make_ep_path(new_id)
			move(old_path, new_path)
	
def make_ep_path(id):
	"""Construct ep path with id"""
	return profile_get("pool/" + safefilepath(id + ".json"))
	
def get_ep_path(mission):
	"""Return episode save file path"""
	return make_ep_path(get_mission_id(mission))
	
load_episodes_status = {}
load_episodes_lock = threading.Lock()

@contextlib.contextmanager
def load_episodes(mission):
	mission_id = id(mission)
	with load_episodes_lock:
		if not mission.episodes:
			eps = json_load(get_ep_path(mission))
			if eps:
				mission.episodes = [Episode(**e) for e in eps]
		if mission_id in load_episodes_status:
			load_episodes_status[mission_id] += 1
		else:
			load_episodes_status[mission_id] = 1
	debug_log("LOAD_EPISODES")
	try:
		yield
	finally:
		with load_episodes_lock:
			if load_episodes_status[mission_id] == 1:
				if mission.episodes:
					file = get_ep_path(mission)
					json_dump(mission.episodes, file)
					mission.episodes = None
				del load_episodes_status[mission_id]
			else:
				load_episodes_status[mission_id] -= 1
		debug_log("UNLOAD_EPISODES")

def cleanup_episode(mission):
	"""Remove episode save file. (probably because the mission is removed from
	the mission manager)
	"""
	remove(get_ep_path(mission))
