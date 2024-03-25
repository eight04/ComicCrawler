from time import time

from worker import Worker, WorkerExit, sleep

from .analyzer import Analyzer
from .episode_loader import load_episodes

class BatchAnalyzer:
	def __init__(
		self,
		gen_missions,
		stop_on_error=True,
		on_item_finished=None,
		on_finished=None
	):
		self.thread = Worker(self.analyze)
		self.gen_missions = gen_missions
		self.on_finished = on_finished
		self.on_item_finished = on_item_finished
		self.stop_on_error = stop_on_error
		self.cooldown = {}
		
	def start(self):
		self.thread.start()
		return self
		
	def stop(self):
		self.thread.stop()
		return self
		
	def get_cooldown(self, mission):
		if not hasattr(mission.module, "rest_analyze"):
			return 0
		pre_ts = self.cooldown.get(mission.module.name)
		if pre_ts is None:
			return 0
		cooldown = mission.module.rest_analyze - (time() - pre_ts)
		return cooldown if cooldown > 0 else 0
		
	def analyze(self):
		err = None
		try:
			self.do_analyze()
		except WorkerExit:
			raise
		except BaseException as _err:
			err = _err
			raise
		finally:
			if self.on_finished:
				self.on_finished(err)
			
	def do_analyze(self):
		for mission in self.gen_missions:
			err = None
			try:
				sleep(self.get_cooldown(mission))
				with load_episodes(mission):
					Analyzer(mission).analyze()
			except WorkerExit:
				raise
			except BaseException as _err: # pylint: disable=broad-except
				err = _err
				if self.stop_on_error and (not callable(self.stop_on_error) or self.stop_on_error(err)):
					err.mission = mission
					raise
				sleep(3)
			finally:
				if self.on_item_finished:
					self.on_item_finished(err, mission)
				self.cooldown[mission.module.name] = time()		
