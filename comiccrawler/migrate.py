#! python3

def migrate():
	# 20150608
	import pickle
	from . import MissionManager, io
	from .core import Mission, Episode
	from .safeprint import safeprint
	
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
		return Episode(
			title=ep.title,
			url=ep.firstpageurl,
			current_url=getattr(ep, "currentpageurl", None),
			current_page=getattr(ep, "currentpagenumber", 0),
			skip=getattr(ep, "skip", False),
			complete=getattr(ep, "complete", False)
		)
			
	def put_missions(file, pool_name):
	
		print("Process " + file)
		
		if not io.is_file(file):
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
