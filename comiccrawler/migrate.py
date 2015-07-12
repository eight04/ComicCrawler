#! python3

def migrate():
	# 20150608
	import pickle
	from .mission_manager import MissionManager
	from .core import Mission, Episode
	from .safeprint import safeprint
	from .io import is_file

	print("Create mission manager...")
	mission_manager = MissionManager()
	mission_manager.load()

	class OldMission: pass
	class OldEpisode: pass

	class Unpickler(pickle.Unpickler):
		def find_class(self, module, name):
			if (module, name) == ("comiccrawler", "Mission"):
				return OldMission
			if (module, name) == ("comiccrawler", "Episode"):
				return OldEpisode
			return super().find_class(module, name)

	def get_new_ep(ep):
		new_ep = Episode(
			title=ep.title,
			url=ep.firstpageurl,
			current_url=getattr(ep, "currentpageurl", None),
			current_page=getattr(ep, "currentpagenumber", 0),
			skip=getattr(ep, "skip", False),
			complete=getattr(ep, "complete", False)
		)
		if new_ep.current_url is True:
			new_ep.current_url = new_ep.url
		return new_ep

	def put_missions(file, pool_name):

		print("Process " + file)

		if not is_file(file):
			print("Can't find " + file)
			return

		print("Load old datas")
		with open(file, "rb") as f:
			missions = Unpickler(f).load()

		for mission in missions:
			safeprint("Convert to new mission: " + mission.title)
			new_mission = Mission(
				title=mission.title,
				state=mission.state,
				url=mission.url,
				episodes=[get_new_ep(ep) for ep in mission.episodelist]
			)
			mission_manager.add(pool_name, new_mission)

	put_missions("save.dat", "view")
	put_missions("library.dat", "library")

	print("Mission manager save files...")
	mission_manager.save()
