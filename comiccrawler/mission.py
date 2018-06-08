from threading import Lock

from .error import ModuleError
from .channel import mission_ch

class Mission:
	"""Create Mission object. Contains information of the mission."""

	def __init__(self, title=None, url=None, episodes=None, state="INIT"):
		"""Construct."""
		from .mods import get_module

		super().__init__()

		self.title = title
		self.url = url
		self.episodes = episodes
		self.state = state
		self.module = get_module(url)
		if not self.module:
			raise ModuleError("Get module failed!")
			
mission_lock = Lock()
class MissionProxy:
	"""Publish MISSION_PROPERTY_CHANGED event when property changed"""
	def __init__(self, mission):
		self.__dict__["mission"] = mission

	def __getattr__(self, name):
		return getattr(self.mission, name)

	def __setattr__(self, name, value):
		with mission_lock:
			setattr(self.mission, name, value)
		mission_ch.pub("MISSION_PROPERTY_CHANGED", self)

	def tojson(self):
		json = vars(self.mission).copy()
		del json["module"]
		return json

def create_mission(*args, **kwargs):
	return MissionProxy(Mission(*args, **kwargs))
