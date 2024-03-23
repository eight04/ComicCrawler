import re
import time
import traceback
from urllib.parse import urlparse

from worker import WorkerExit, sleep

from .channel import download_ch
from .module_grabber import ModuleGrabber
from .error import SkipPageError, PauseDownloadError, LastPageError
from .safeprint import print

class EpisodeList:
	def __init__(self, eps=()):
		self.list = []
		self.title_set = set()
		self.url_set = set()
		for ep in eps:
			self.add(ep)
	
	def add(self, ep):
		if ep in self:
			return False
		self.list.append(ep)
		self.url_set.add(ep.url)
		self.title_set.add(ep.title)
		return True
		
	def __contains__(self, ep):
		if ep.url in self.url_set:
			return True
		if ep.title in self.title_set:
			return True
		return False
		
	def __iter__(self):
		return iter(self.list)
		
	def __len__(self):
		return len(self.list)
		
	def __reversed__(self):
		return reversed(self.list)

class Analyzer:
	"""Analyze mission"""
	def __init__(self, mission):
		self.mission = mission
		self.grabber = ModuleGrabber(mission.module)
		self.old_urls = None
		self.old_titles = None
		self.is_new = not mission.episodes
		self.html = None
		
	def analyze(self):
		"""Start analyze"""
		try:
			self.do_analyze()
		except BaseException:
			# correctly handle mission state
			self.mission.state = "ERROR"
			raise
		
	def do_analyze(self):
		"""Analyze inner"""
		print("Start analyzing {}".format(self.mission.url))

		self.mission.state = "ANALYZING"
		
		# one-time mission
		if self.is_onetime():
			print("It's one-time mission")
			ep = self.mission.episodes[0]
			if ep.skip or ep.complete:
				self.mission.state = "FINISHED"
			else:
				self.mission.state = "UPDATE"
			print("Analyzing success!")
			return
			
		self.html = self.grabber.html(self.mission.url, retry=True)
		
		if not self.mission.title:
			self.mission.title = self.mission.module.get_title(
				self.html, self.mission.url)
				
		self.analyze_pages()
				
		if self.is_new:
			self.mission.state = "ANALYZED"
			
		elif all(e.complete or e.skip for e in self.mission.episodes):
			self.mission.state = "FINISHED"
			
		else:
			self.mission.state = "UPDATE"

		print("Analyzing success!")
		
	def analyze_pages(self):
		"""Crawl for each pages"""
		url = self.mission.url
		old_eps = EpisodeList(self.mission.episodes or ())
		new_eps = EpisodeList()
		
		while True:
			try:
				eps = list(self.mission.module.get_episodes(self.html, url))
			except SkipPageError:
				pass
			except LastPageError:
				break
			else:
				if not eps:
					print("Warning: get_episodes returns an empty list")
				self.transform_title(eps)
				
				eps = EpisodeList(eps)
				
				# add result episodes into new_eps in new to old order.
				for ep in reversed(eps):
					new_eps.add(ep)
					
				# FIXME: do we really need this check?
				# one-time mission?
				if self.is_onetime(new_eps):
					break
					
				# duplicate with old_eps
				if any(e in old_eps for e in eps):
					break
				
			# get next page
			next_url = self.get_next_page(self.html, url)
			if not next_url:
				break
			url = next_url
			print('Analyzing {}...'.format(url))
			sleep(getattr(self.mission.module, "rest_analyze", 0))
			r = urlparse(self.mission.url)
			self.html = self.grabber.html(url, retry=True, header={
				"Referer": self.mission.url,
				"Origin": f"{r.scheme}://{r.netloc}"
				})
		
		has_new_ep = False
		for ep in reversed(new_eps):
			if old_eps.add(ep):
				has_new_ep = True
		self.mission.episodes = list(old_eps)
		
		if has_new_ep:
			self.mission.last_update = time.time()
		
		if not self.mission.episodes:
			raise TypeError("Episode list is empty")
			
	def get_next_page(self, html, url):
		if not hasattr(self.mission.module, "get_next_page"):
			return None
		return self.mission.module.get_next_page(html, url)
			
	def transform_title(self, eps):
		format = self.mission.module.config.get("titlenumberformat")
		if not format:
			return
		for ep in eps:
			# ignore mission title if exists
			title = list(ep.title.partition(self.mission.title))
			for i in (0, 2):
				title[i] = format_title_number(title[i], format)
			ep.title = "".join(title)
			
	def is_onetime(self, it=None):
		"""Check if the mission should only be analyze once"""
		if it is None:
			it = self.mission.episodes
		return it and len(it) and first(it).url == self.mission.url

def analyze(mission):
	"""Analyze mission."""
	try:
		Analyzer(mission).analyze()

	except WorkerExit: # pylint: disable=try-except-raise
		raise

	except Exception as err: # pylint: disable=broad-except
		traceback.print_exc()
		download_ch.pub("ANALYZE_FAILED", (err, mission))

	except PauseDownloadError as err:
		download_ch.pub("ANALYZE_INVALID", (err, mission))

	else:
		download_ch.pub("ANALYZE_FINISHED", mission)
		
def format_title_number(title, format):
	"""第3卷 --> 第003卷"""
	def replacer(match):
		number = match.group()
		return format.format(int(number))
	return re.sub(r"\d+", replacer, title)

def first(s):
	return next(iter(s))
	
