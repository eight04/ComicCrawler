from time import time

from worker import Worker, WorkerExit, sleep

from .analyzer import Analyzer
from .episode_loader import load_episodes

class BatchAnalyzer:
	def __init__(
		self,
		gen_missions,
		stop_on_error=True,
		done_item=None,
		done=None
	):
		self.thread = Worker(self.analyze)
		self.gen_missions = gen_missions
		self.done = done
		self.done_item = done_item
		self.stop_on_error = stop_on_error
		self.cooldown = {}
		self.last_err = None
		
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
		self.last_err = None
		try:
			self.do_analyze()
		finally:
			if self.done:
				self.done(self.last_err)
			
	def do_analyze(self):
		for mission in self.gen_missions:
			try:
				sleep(self.get_cooldown(mission))
				with load_episodes(mission):
					Analyzer(mission).analyze()
			except BaseException as err: # catch PauseDownloadError and WorkerExit?
				self.last_err = err
				if self.done_item:
					self.done_item(err, mission)
				if self.stop_on_error and (not callable(self.stop_on_error) or self.stop_on_error(err)):
					break
				if isinstance(err, WorkerExit):
					raise
			else:
				if self.done_item:
					self.done_item(None, mission)
			finally:
				self.cooldown[mission.module.name] = time()		
