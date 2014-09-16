#! python3

"""Comic Crawler."""

import re
from safeprint import safeprint

import urllib.request
import urllib.parse
import urllib.error

# state code definition
INIT = 0
ANALYZED = 1
DOWNLOADING = 2
PAUSE = 3
FINISHED = 4
ERROR = 5
INTERRUPT = 6
UPDATE = 7
ANALYZING = 8

from queue import Queue
messageBucket = Queue()
def _evtcallback(msg, *args):
	"""Message collector"""
	
	messageBucket.put((msg, args))
	
def getext(byte):
	"""Test the file type according byte stream with imghdr
	
	imghdr issue: http://bugs.python.org/issue16512
	"""
	
	import imghdr
	r = imghdr.what("", byte)
	if r:
		if r.lower() == "jpeg":
			return "jpg"
		return r.lower()
	
	h = byte
	if h[:2] == b"\xff\xd8":
		return "jpg"
	
	if h[:3] == b"CWS" or h[:3] == b"FWS":
		return "swf"

	if h[:4] == b"8BPS":
		return "psd"

	if h[:7] == b"Rar!\x1a\x07\x00":
		return "rar"
		
	if h[:4] == b"PK\x03\x04":
		return "zip"
		
	return None
			
def createdir(path):
	"""Create folder of filepath. 
	
	This function can handle sub-folder like 
	"this_doesnt_exist\sure_this_doesnt_exist_either\I_want_to_create_this"
	"""
	import os, os.path
	
	path = os.path.normpath(path)
	
	try:
		os.mkdir(path)
	except FileExistsError:
		pass
	except FileNotFoundError as er:
		a, b = os.path.split(path)
		createdir(a)
		createdir(path)
	
def safefilepath(s):
	"""Return a safe directory name. Return string."""

	return re.sub("[/\\\?\|<>:\"\*]","_",s).strip()
	
def safeurl(url):
	"""Return a safe url, quote the unicode characters."""
	
	base = re.search("(https?://[^/]+)", url).group(1)
	path = url.replace(base, "")
	def u(match):
		return urllib.parse.quote(match.group())
	path = re.sub("[\u0080-\uffff \[\]]+", u, path)
	# safeprint(base + path)
	return base + path
	
def safeheader(header):
	"""Return a safe header, quote the unicode characters."""
	
	def u(match):
		return urllib.parse.quote(match.group())
	for key in header:
		header[key] = re.sub("[\u0080-\uffff]+", u, header[key])
		
	return header

def grabber(url, header={}, encode=False):	
	"""Http works"""
	
	url = safeurl(url)
	# bugged when header contains non latin character...
	header = safeheader(header)
	req = urllib.request.Request(url,headers=header)
	rs = urllib.request.urlopen(req, timeout=20)
	ot = rs.read()
	
	if not encode:
		return ot
		
	# find html defined encoding
	html = ot.decode("utf-8", "replace")
	r = re.search(r"charset=[\"']?([^\"'>]+)", html)
	if r:
		encode = r.group(1)
		return ot.decode(encode, "replace")
	return html

def grabhtml(url, hd={}, encode="utf-8"):
	"""Get html source of given url. Return String."""
	
	return grabber(url, hd, encode)

def grabimg(url, hd={}):
	"""Return byte stream."""
	
	return grabber(url, hd)


class Mission:
	"""Mission data class. Contains a mission's information."""
	
	def __init__(self):
		"""Use title, url, episodelist, state, downloader, lock"""
		from threading import Lock
		
		self.title = ""
		self.url = ""
		self.episodelist = []
		self.state = INIT
		self.downloader = None
		self.lock = Lock()
		self.update = False
		
	def state_(self, state=None):
		"""Call this method to make a MISSION_STATE_CHANGE message"""
		
		if not state:
			return self.state
		self.state = state
		_evtcallback("MISSION_STATE_CHANGE", self)
			
	def __getstate__(self):
		"""pickle"""
	
		state = self.__dict__.copy()
		del state["downloader"]
		del state["lock"]
		return state
		
	def __setstate__(self, state):
		"""unpickle"""
		from threading import Lock
		
		self.__dict__.update(state)
		self.lock = Lock()
		# backward compatibility
		if not hasattr(self, "update"):
			self.update = False
		
	def setTitle(self, title):
		"""set new title"""
		
		self.title = title
		_evtcallback("MISSION_TITLE_CHANGE", self)
		
	def set(self, **kwargs):
		"""Set new attribute, may replace setTitle later."""
		
		for key, value in kwargs.items():
			if key in self:
				setattr(self, key, value)

class Episode:
	"""Episode data class. Contains a book's information."""
	
	def __init__(self):
		"""init"""
		
		self.title = ""
		self.firstpageurl = ""
		self.currentpageurl = ""
		self.currentpagenumber = 0
		self.skip = False
		self.complete = False
		self.error = False
		self.errorpages = 0
		self.totalpages = 0

		
"""Message flag"""

BUBBLE = 1
BROADCAST = 2

class MessageError: pass

class MessageTree:
	"""Message pattern"""
	
	def __init__(self, parent):
		self.parent = parent
		self.children = set()
		self.messageBucket = queue.Queue()
		self.messageCached = []
	
	def sendMessage(getter, message, param=None, flag=0):
		"""Send message to other threads"""
		
		getter.message(message, param, flag, self)
		
	def message(self, message, param=None, flag=0, sender=None):
		"""Put message into messagBucket
		
		flags: BUBBLE/BROADCAST
		"""
		self.messageBucket.put((message, param, flag, sender))
		
	def transferMessage(self, message, param, flag, sender):
		"""Bubble and broadcast"""
		
		if BUBBLE & flag and self.parent and self.parent != sender:
			self.sendMessage(self.parent, message, param, flag)
			
		if BROADCAST & flag:
			for child in self.children:
				if child != sender:
					self.sendMessage(child, message, param, flag)
	
	def _onMessage(self, message, param, flag, sender):
		"""Message holder container, to ensure to transfer message"""
		
		self.transferMessage(message, param, flag, sender)
		ret = onMessage(message, param, sender)
		return ret
		
	def onMessage(self, message, param, sender):
		"""Override"""
		pass

	def wait(self, arg, sender=None):
		"""Wait for specify message or wait specify duration.
		
		`arg` could be int or str. If `arg` is int, this function will wait 
		`arg` seconds. 
		
		If arg is str, this function will take the second param `sender`.
		If sender is provided, this function will wait till getting specify
		message `arg` which was sent by `sender`. If sender is None, this 
		function just returned after getting specify message.
		"""
		if type(arg) in [int, float]:
			import time
			
			while True:
				timeIn = time.time()
				try:
					message = self.messageBucket.get(timeout=arg)
				except queue.Empty:
					return
				else:
					ret = self._onMessage(*message)
					self.messageCached.append((message, ret))
					arg -= time.time() - timeIn
				
		elif type(arg) is str:
			cached = None
			for cache in self.messageCached:
				if cache[0][0] == arg and (not sender or sender == cache[0][3]):
					cached = cache
			if cached:
				self.messageCached.remove(cached)
				return cached[1]	# cached result
				
			while True:
				message = self.messageBucket.get()
				ret = self._onMessage(*message)
				if message[0] == arg and (not sender or sender == message[3]):
					return ret
				self.messageCached.append((message, ret))

	def createChild(self, cls, *args, **kw):
		"""Broadcast message to child"""
		
		if not issubclass(cls, MessageTree):
			raise MessageError("Created children failed: " + cls + " doesn't inherit MessageTree.")
		child = cls(self, *args, **kw)
		self.children.add(child)
		return child
		
		
class Worker(MessageTree):
	"""Wrap Thread class. Inherit MessageTree for thread communication."""
	
	def __init__(self, parent=None, target=None, *args, **kw):
		"""init"""
		super().__init__(parent)
		
		self.error = queue.Queue()
		if callable(target):
			from functools import partial
			self.worker = partial(target, *args, **kw)
		self.threading = None
		
	def _worker(self):
		"""Real target to pass to threading.Thread"""

		self.running = True
		
		try:
			self.ret = self.worker()
		except InterruptError:
			pass
		except Exception as er:
			self.error.put(er)

		try:
			self.cleanup()
		except Exception as er:
			self.error.put(er)
		
		self.stopChildThread()
		while len(self.childThreads):
			self.wait("CHILD_THREAD_END")
		
		self.running = False
		if self.parent:
			self.sendMessage(self.parent, "CHILD_THREAD_END")
		
	def worker(self):
		"""Override"""
		pass
		
	def cleanup(self, *args, **kwargs):
		"""Override"""
		pass
		
	def stopChildThread(self):
		"""Stop all child threads"""
		
		for thread in self.children:
			self.sendMessage(thread, "STOP_THREAD", None, BROADCAST)

	def start(self):
		"""call this method and self.worker will run in new thread"""
		import threading

		if self.running:
			return False
		self.threading = threading.Thread(target=self._worker)
		self.threading.start()
		return self
		
	def stop(self):
		"""Warning! stop() won't block. 
		
		you should use join() to ensure the thread was killed.
		"""
		self.message("STOP_THREAD", None, BROADCAST)
		
	def onMessage(self, message, param, sender):
		"""Override"""
		super().onMessage(message, param, sender)
		
		if message == "STOP_THREAD":
			raise InterruptError
			
		if message == "CHILD_THREAD_END":
			self.childThreads.remove(sender)
			return sender	
		
	def join(self):
		"""thread join method."""

		self.threading.join()
		
	def waitChild(self, func, *args, **kw):
		child = self.createChild(Worker, func, *args, **kw).start()
		self.wait("CHILD_THREAD_END", child)
		if child.error:
			raise ThreadError("Error when executing child thread!", child.error)
		return child.ret
		
class DownloadWorker(Worker):
	"""The main core of Comic Crawler"""

	def __init__(self, parent, mission=None, savepath="."):
		"""set the mission"""
		super().__init__(parent)
		
		self.mission = mission
		self.savepath = savepath
	
	def worker(self):
		"""download worker"""
		
		# warning there is a deadlock, 
		# never do mission.lock.acquire in callback...
		try:
			self.mission.lock.acquire()
			self.download(self.mission, self.savepath)
		except InterruptError:
			self.mission.state_(PAUSE)
			self.callback(self.mission)
		except Exception as er:
			self.mission.state_(ERROR)
			self.callback(self.mission, er)
		else:
			self.mission.state_(FINISHED)
			self.callback(self.mission)
		finally:
			self.mission.lock.release()
			
	def download(self, mission, savepath):
		"""Start mission download. This method will call cls.crawlpage()
		for each episode.
		
		"""
		import os.path
		
		safeprint("total {} episode.".format(len(mission.episodelist)))
		for ep in mission.episodelist:
			if ep.skip or ep.complete:
				continue
				
			# deside wether to generate Episode folder, or it will put every 
			# images file in one folder. Ex. pixiv.net
			if ("noepfolder" in mission.downloader.__dict__ and 
					mission.downloader.noepfolder):
				efd = os.path.join(savepath, safefilepath(mission.title))
				fexp = safefilepath(ep.title) + "_{:03}"
			else:
				efd = os.path.join(savepath, safefilepath(mission.title), 
						safefilepath(ep.title))
				fexp = "{:03}"
			
			safeprint("Downloading ep {}".format(ep.title))
			try:
				self.crawlpage(ep, efd, mission, fexp)
			except LastPageError:
				safeprint("Episode download complete!")
				print("")
				ep.complete = True
				_evtcallback("DOWNLOAD_EP_COMPLETE", mission, ep)
			except SkipEpisodeError:
				safeprint("Something bad happened, skip the episode.")
				ep.skip = True
				continue
		else:
			safeprint("Mission complete!")
			mission.state_(FINISHED)
			mission.update = False

	def crawlpage(self, ep, savepath, mission, fexp):
		"""Crawl all pages of an episode.
		
		Grab image into savepath. To exit the method, raise LastPageError.
		
		Should define error handler for grabimg failed. Note the error by
		setting episode.errorpages, episode.currentpagenumber, episode.
		totalpages, episode.currentpageurl.
		
		"""
		import time, os, os.path
		
		downloader = mission.downloader
		
		if not ep.currentpagenumber:
			ep.currentpagenumber = 1
		if not ep.currentpageurl:
			ep.currentpageurl = ep.firstpageurl
			
		imgurls = None
		if "getimgurls" in downloader.__dict__:
			# we can get all img urls from first page
			errorcount = 0
			while True:
				try:
					html = self.waitChild(grabhtml, ep.firstpageurl, downloader.header)
					imgurls = self.waitChild(downloader.getimgurls, html, url=ep.firstpageurl)
					
					if not imgurls:
						raise EmptyImageError
						
				except (LastPageError, SkipEpisodeError, InterruptError) as er:
					raise er
					
				except Exception as er:
					safeprint("get imgurls failed: {}".format(er))
					errorcount += 1
					if errorcount >= 10:
						raise TooManyRetryError
					if "errorhandler" in downloader.__dict__:
						downloader.errorhandler(er, ep)
					self.wait(5)
				else:
					break
				
		ep.imgurls = imgurls
		
		if imgurls and len(imgurls) < ep.currentpagenumber:
			raise LastPageError

		
		# some file already in directory
		createdir(savepath)
		downloadedlist = [ i.rpartition(".")[0] for i in os.listdir(savepath) ]
		
		# crawl all pages
		errorcount = 0
		while True:
			safeprint("Crawling {} {} page {}...".format(mission.title, 
					ep.title, ep.currentpagenumber))
			try:
				if not imgurls:
					# getimgurl method
					html = self.waitChild(
						grabhtml, 
						ep.currentpageurl, 
						hd=downloader.header
					)
					
					imgurl = self.waitChild(
						downloader.getimgurl, 
						html, 
						url=ep.currentpageurl
						page=ep.currentpagenumber, 
					)
					
					nextpageurl = self.waitChild(
						downloader.getnextpageurl,
						ep.currentpagenumber, 
						html, 
						url=ep.currentpageurl
					)
					
					if type(imgurl) is tuple:
						imgurl, header = imgurl
					else:
						header = downloader.header
				else:
					# getimgurls method
					imgurl = imgurls[ep.currentpagenumber - 1]
					header = downloader.header
					nextpageurl = ep.currentpagenumber < len(imgurls)
				
				# generate file name
				fn = fexp.format(ep.currentpagenumber)
				
				# file already exist
				if fn in downloadedlist:
					raise ImageExistsError
					
				safeprint("Downloading page {}: {}".format(
						ep.currentpagenumber, imgurl))
						
				oi = self.waitChild(grabimg, imgurl, hd=header)
				
				# check image type
				ext = getext(oi)
				if not ext:
					raise Exception("Invalid image type.")
					
			except ImageExistsError:
				safeprint("...page {} already exist".format(
						ep.currentpagenumber))
						
			except InterruptError as er:
				raise er
				
			except Exception as er:
				safeprint("Crawl page error: {}".format(er or type(er)))
				errorcount += 1
				if errorcount >= 10:
					raise TooManyRetryError
				downloader.errorhandler(er, ep)
				
				self.wait(5)
				continue
				
			else:
				# everything is ok, save image
				with open(os.path.join(savepath, "{}.{}".format(fn, ext)), "wb") as f:
					f.write(oi)
				
			# something have to rewrite, check currentpage url rather than
			# nextpage. Cuz sometime currentpage doesn't exist either.
			if not nextpageurl:
				ep.complete = True
				raise LastPageError
			ep.currentpageurl = nextpageurl
			ep.currentpagenumber += 1
			errorcount = 0
			print("")
	
class AnalyzeWorker(Worker):
	"""Analyze the mission.url, also the core of Comic Crawler"""

	def __init__(self, parent, mission=None):
		"""set mission"""
		super().__init__(parent)
		
		self.mission = mission
	
	def worker(self):
		"""analyze worker"""
		
		try:
			self.mission.lock.acquire()
			self.analyze(self.mission)
		except Exception as er:
			self.mission.state = ERROR
			import traceback
			er_message = traceback.format_exc()
			safeprint(er_message)
			self.callback(self.mission, er, er_message)
		else:
			self.mission.state = ANALYZED
			self.callback(self.mission)
		finally:
			self.mission.lock.release()

	def removeDuplicateEP(self, mission):
		"""remove duplicate episode"""
		
		list = []
		for ep in mission.episodelist:
			for e in list:
				if ep.firstpageurl == e.firstpageurl:
					print("duplicate")
					break
			else:
				list.append(ep)
		mission.episodelist = list
	
			
	def analyze(self, mission):
		"""Analyze mission url."""
		
		# debug
		self.removeDuplicateEP(mission)
		
		safeprint("start analyzing {}".format(mission.url))
		mission.state_(ANALYZING)

		downloader = mission.downloader
		print("grabbing html")
		html = self.waitChild(grabhtml, mission.url, hd=downloader.header)
		print("getting title")
		mission.title = downloader.gettitle(html, url=mission.url)
		print("getting episode list")
		epList = self.waitChild(downloader.getepisodelist, html, url=mission.url)
		if not mission.episodelist:
			# new mission
			mission.episodelist = epList
			mission.state_(ANALYZED)
		else:
			# re-analyze, put new ep into eplist
			for ep in epList:
				for oep in mission.episodelist:
					if oep.firstpageurl == ep.firstpageurl:
						# found
						break
				else:
					mission.episodelist.append(ep)
			# check if there are incomplete ep
			for ep in mission.episodelist:
				if not ep.complete and not ep.skip:
					mission.state_(UPDATE)
					mission.update = True
					break
			else:
				mission.state_(FINISHED)
		
		if not mission.episodelist:
			raise Exception("get episode list failed!")
		
		safeprint("analyzed succeed!")

class ThreadError(Exception):
	"""Error generated by threads"""
	def __init__(self, message, errors):
		super().__init__(message)
		
		self.errors = errors
	
	def __str__(self):
		return self.errors

class InterruptError(ThreadError): pass

class CrawlerError(Exception): pass

class ImageExistsError(CrawlerError): pass

class LastPageError(CrawlerError): pass

class TooManyRetryError(CrawlerError): pass

class EmptyImageError(CrawlerError): pass

class SkipEpisodeError(CrawlerError): pass

class ModuleError(CrawlerError): pass

class FreeQue:
	"""Mission queue data class."""
	
	def __init__(self, savepath=None):
		self.q = []
		self.savepath = savepath
		
	def contains(self, mission):
		for m in self.q:
			if q.url == mission.url:
				return True
		return False
	
	def empty(self):
		"""return true if list is empty"""
		return not self.q
	
	def put(self, item):
		"""append item"""
		self.q.append(item)
		_evtcallback("MISSIONQUE_ARRANGE", self)
		
	def lift(self, items, reverse=False):
		"""Move items to the top."""
		a = [ i for i in self.q if i in items ]
		b = [ i for i in self.q if i not in items ]
		if not reverse:
			self.q = a + b
		else:
			self.q = b + a
		_evtcallback("MISSIONQUE_ARRANGE", self)
	
	def drop(self, items):
		"""Move items to the bottom."""
		self.lift(items, reverse=True)
		
	def remove(self, items):
		"""Delete specify items."""
		self.q = [ i for i in self.q if i not in items]
		_evtcallback("MISSIONQUE_ARRANGE", self)
		_evtcallback("MESSAGE", "Deleted {} mission(s)".format(len(items)))

	def take(self, n=1):
		"""Return a list containing n valid missions. If n <= 1 return a valid 
		mission.
		"""
		if n <= 1:
			for i in self.q:
				if i.state != FINISHED:
					return i
			return None
		else:
			s = []
			for i in self.q:
				if i.state != FINISHED:
					s.append(i)
				if len(s) == n:
					return s
			return s or None
			
	def cleanfinished(self):
		"""delete fished missions"""
		self.q = [ i for i in self.q if i.state is not FINISHED ]
		_evtcallback("MISSIONQUE_ARRANGE", self)
		
	def printList(self):
		"""print mission list"""
		for m in self.q:
			print(m.title)
			
	def getList(self):
		"""return title list"""
		return [m.title for m in self.q]
		
	def load(self):
		"""unpickle list from file"""
		if not self.savepath:
			return
		import pickle
		try:
			f = open(self.savepath, "rb")
		except FileNotFoundError:
			print("no lib file")
			return
		self.q = pickle.load(f)
		_evtcallback("MISSIONQUE_ARRANGE", self)
		
	def save(self):
		"""pickle list to file"""
		if not self.savepath:
			return
		import pickle
		f = open(self.savepath, "wb")
		pickle.dump(self.q, f)

class ConfigManager:
	"""Load config for other classes"""

	def __init__(self, path):
		"""set config file path"""
		import configparser as cp
		self.path = path
		self.config = cp.ConfigParser(interpolation=None)
		
		self.load()
		
	def get(self):
		"""return config"""
		return self.config
		
	def load(self):
		"""read config from file
		
		There's a utf-8 issue with configparser:
		http://bugs.python.org/issue14311
		"""
		self.config.read(self.path, "utf-8-sig")
		
	def save(self):
		with open(self.path, "w", encoding="utf-8") as f:
			self.config.write(f)
		
	@classmethod
	def apply(cls, config, dict, overwrite=False):
		"""ConfigManager.apply(dict1, dict2, overwrite)
		
		copy dict2 into dict1
		"""
		for key, value in dict.items():
			if not overwrite and key in config:
				continue
			config[key] = value
		return

class DownloadManager(Worker):
	"""DownloadManager class. Maintain the mission list."""
	
	def __init__(self, configManager=None, moduleManager=None):
		"""set controller"""
		super().__init__()
		
		self.configManager = configManager
		self.moduleManager = moduleManager
		self.missions = FreeQue("save.dat")
		self.library = FreeQue("library.dat")
		self.downloadWorker = None
		self.libraryWorker = None
		self.state = "INIT"
		
		self.conf()
		self.load()
		
	def conf(self):
		"""Load config from controller. Set default"""		
		import os.path
		
		conf = self.configManager
		self.setting = conf.get()["DEFAULT"]
		default = {
			"savepath": "download",
			"runafterdownload": ""
			"libraryautocheck": "true"
		}
		conf.apply(self.setting, default)
		# clean savepath
		self.setting["savepath"] = os.path.normpath(self.setting["savepath"])
		
	def addMission(self, mission):
		"""add mission"""
		if self.library.match(mission):
			raise Error("Mission already in library")
		self.missions.put(mission)
		
	def removeMission(self, *args):
		pass
	
	def startDownload(self):
		"""Start downloading"""
		if self.state not in ["STOP", "INIT"]:
			return
			
		mission = self.missions.take()
		if not mission:
			raise Error("All download completed")
		self.downloadWorker = self.createChildThread(DownloadWorker, mission).start()
		self.state = "DOWNLOADING"
		
	def stopDownload(self):
		"""Stop downloading"""
		if self.state in ["STOP", "INIT"]:
			return
		self.downloadWorker.stop()
		
	def startCheckUpdate(self):
		"""Start check library update"""
		if self.library and self.libraryWorker.running:
			return
		
		mission = self.library.take()
		self.libraryWorker = self.createChildThread(AnalyzeWorker, mission).start()
		
	def worker(self):
		"""Event loop"""
		while True:
			self.wait()
		
	def onMessage(self, message, param, thread):
		"""Check worker state"""
		if message == "CHILD_THREAD_END":
			if thread == self.downloadWorker:
				command = self.setting["runafterdownload"]
				if not command:
					continue
				try:
					from subprocess import call
					call((command, "{}/{}".format(self.setting["savepath"], safefilepath(thread.mission.title))))
				except Exception as er:
					safeprint("failed to run process: {}".format(er))
					
				mission = self.missions.take()
				if not mission:
					self.state = "STOP"
					raise Error("All download completed")
				self.downloadWorker = self.createChildThread(DownloadWorker, mission).start()
				
			if thread == self.libraryWorker:
				mission = self.library.take()
				if not mission:
					return
				self.libraryWorker = self.createChildThread(AnalyzeWorker, mission).start()
	
	def save(self):
		"""Save mission que."""
		
		try:
			self.missions.save()
			self.library.save()
		except Exception as er:
			self.message("DAT_SAVE_FAILED", er)
		else:
			print("Session saved success.")
		
	def load(self):
		"""load mission que"""
		
		try:
			self.missions.load()
			self.library.load()
		except Exception as er:
			self.message("DAT_LOAD_FAILED", er)
		else:
			for m in self.missions.q:
				m.downloader = self.moduleManager.getDownloader(m.url)
			print("Session loaded success.")
		self.removeLibDuplicate()
		
	def replaceDuplicate(self, list):
		"""replace duplicate with library one"""
		
		l = self.missionque.q
		for i, mission in enumerate(l):
			for new_mission in list:
				if mission.url == new_mission.url:
					l[i] = new_mission
		
	def addLibrary(self, mission):
		"""add mission"""
		
		if self.library.contains(mission):
			raise Error("Mission already exist!")
		self.library.put(mission)
		
	def removeLibrary(self, *missions):
		"""remove missions"""
		
		self.library.remove(missions)
		
		
class ModuleManager:
	"""Import all the downloader module.
	
	DLModuleManger will automatic import all modules in the same directory 
	which prefixed with filename "cc_".
	
	"""
	
	def __init__(self, configManager = None):
		import os
		self.configManager = configManager
		self.dlHolder = {}
		self.mods = []
		self.mod_dir = os.path.dirname(os.path.realpath(__file__))
		
		self.loadconfig()
		self.loadMods()
		self.registHolders()
		
	def loadMods(self):
		"""Load mods to self.mods"""
		import importlib, os
		
		for f in os.listdir(self.mod_dir):
			if not re.search("^cc_.+\.py$", f):
				continue
			mod = f.replace(".py","")
			self.mods.append(importlib.import_module(mod))
		
	def registHolders(self):
		"""Regist domain with mod to self.dlHolder"""
		
		for mod in self.mods:
			for url in mod.domain:
				self.dlHolder[url] = mod

		
	def loadconfig(self):
		"""Load setting.ini and set up module.
		"""
	
		config = self.configManager.get()
		for d in self.mods:
			if "loadconfig" in d.__dict__:
				d.loadconfig(config)
		
	def getdlHolder(self):
		"""Return downloader dictionary."""
		return [key for key in self.dlHolder]
		
	def validUrl(self,url):
		"""Return if the url is valid and in downloaders domain."""
		
		if self.getDownloader(url):
			return True
		return False
		
	def getDownloader(self, url):
		"""Return the downloader mod of spect url or return None"""
		
		dm = re.search("https?://([^/]+?)(:\d+)?/", url)
		if dm is None:
			return None
		dm = dm.group(1)
		for d in self.dlHolder:
			if d in dm:
				return self.dlHolder[d]
		return None
		
class Controller:
	"""workflow logic"""
	
	def __init__(self):
		"""Load class -> view -> unload class"""
		
		self.loadClasses()
		self.view()
		self.unloadClasses()
	
	def loadClasses(self):
		"""Load classes"""
		
		self.configManager = ConfigManager("setting.ini")
		self.moduleManager = ModuleManager(self)
		self.downloadManager = DownloadManager(self)
		self.library = Library(self)
		
		
		self.library.load()
		self.downloadManager.load()
		self.downloadManager.replaceDuplicate()
		self.library.checkUpdate()
		
	def unloadClasses(self):
		"""unload classes"""
		
		# wait library stop
		if self.library.running:
			self.library.stop()
			self.library.join()
		self.library.save()
		
		# wait download manager stop
		if self.downloadManager.running:
			self.downloadManager.stop()
			self.downloadManager.join()
		self.downloadManager.save()
		
		# save config
		self.configManager.save()
		
	def view(self):
		"""cli... INCOMPLETE!"""
		
		safeprint("Valid domains: " + " ".join(self.moduleManager.getdlHolder()))
		safeprint("Library list: " + " ".join(self.library.libraryList.getList()))
		safeprint("This is Comic Crawler version " + VERSION + "\n"
			" - Paste an url and press enter to start download.\n"
			" - or use Ctrl+Z to exit.")
			
		while self.getInput():
			pass
			
	def getInput(self):
		"""get input"""
		
		try:
			u = input(">>> ")
		except EOFError:
			return False
			
		command = None
		
		if not u.startswith("http"):
			command, sep, u = u.partition(" ")
			
		if command == "lib":
			self.iLib(u)
			
		elif command == "show":
			self.iShowList(u)
			
		else:
			self.iNewMission(u)
			
		return True

	def iShowList(self, u):
		"""interface: show mission list"""
		
		for m in self.downloadManager.missionque.q:
			safeprint(m.title, m.url, m.state)
				
	def iLib(self, u):
		"""interface: lib command"""
		
		command, sep, u = u.partition(" ")
		
		if command == "add":
			self.iLibAdd(u)
			
		elif command == "remove":
			self.iLibRemove(u)
			
		else:
			self.iLibShow(command)
			
	def iLibShow(self, u):
		"""interface: show lib"""
		
		safeprint(" ".join(self.library.libraryList.getList()))
		
	def iAddUrl(self, url):
		"""interface: when input is an url..."""
		
		downloader = self.moduleManager.getDownloader(url)
		if not downloader:
			print("Unknown url: {}\n".format(url))
			return	
		# construct a mission
		m = Mission()
		m.url = url
		m.downloader = downloader
		
		lm = self.library.exists(m)
		if lm:
			m = lm
		AnalyzeWorker(m, self.iAnalyzeFinished).start()
		
	def iAnalyzeFinished(self, mission, error=None, er_msg=None):
		"""interface: when finished analyzing..."""
		
		if error:
			print("Analyze Failed! " + error)
		else:
			self.iAddMission(mission)
		
	def iAddMission(self, mission):
		"""interface: add mission to download manager"""
		
		self.downloadManager.addmission(mission)
		_evtcallback("MESSAGE", "Queued mission: " + mission.title)
		
	def iStart(self):
		"""interface: start download manager"""
		
		self.downloadManager.start()
		
	def iStop(self):
		"""interface: stop download manager"""
		
		self.downloadManager.stop()
		
	def iClean(self):
		"""interface: remove finished mission in download manager"""
		
		self.downloadManager.missionque.cleanfinished()
		
	def iReloadConfig(self):
		"""interface: reload config"""
		
		self.configManager.load()
		self.moduleManager.loadconfig()
		self.downloadManager.loadconfig()
		
		safeprint("Reload config success!")
		
	def iRemoveMission(self, *args):
		"""interface: remove mission from download manager"""
		
		self.downloadManager.missionque.remove(args)
		
	def iLift(self, *args):
		"""interface: lift missions from download manager"""
		
		self.downloadManager.missionque.lift(args)
		
	def iDrop(self, *args):
		"""interface: drop missions from download manager"""
		
		self.downloadManager.missionque.drop(args)
		
	def iAddToLib(self, mission):
		"""interface: add mission into library"""
	
		self.library.add(mission)
		
	def iLibRemove(self, *args):
		"""interface: remove mission from library"""
		
		self.library.remove(*args)
		
	def iLibCheckUpdate(self):
		"""interface: start library analyzer"""
		
		self.library.checkUpdate()
		
	def iLibDownloadUpdate(self):
		"""interface: add updated mission to download manager"""
		
		self.library.sendToDownloadManager()
		
if __name__ == "__main__":
	
	class CLI:
		def __init__(self):
			import os
			
			self.workingDir = os.getcwd()
			self.scriptDir = os.path.dirname(os.path.realpath(__file__))
			os.chdir(self.scriptDir)
			
			self.configManager = ConfigManager("setting.ini")
			self.moduleManager = ModuleManager(configManager=self.configManager)
			
			from sys import argv
			if len(argv) <= 1:
				self.downloadManager = DownloadManager(
					configManager=self.configManager,
					moduleManager=self.moduleManager
				).start()
				
				self.inputLoop()
			
			elif argv[1] == "domains":
				self.listDomains()
			elif argv[1] == "download":	
				kw = {
					"url": argv[2],
					"savepath": self.workingDir
				}
				if len(argv) >= 5 and argv[3] == "-d":
					kw["savepath"] = os.path.join(self.workingDir, argv[4])
				
				self.start(**kw)
				
		def start(self, url=None, savepath="."):
			if not url:
				return
				
			mission = Mission()
			mission.url = url
			mission.downloader = self.moduleManager.getDownloader(url)
			AnalyzeWorker().analyze(mission)
			DownloadWorker().download(mission, savepath)
			
		def listDomains(self):
			safeprint("Valid domains:\n{}".format(", ".join(self.moduleManager.getdlHolder())))
			
		def inputLoop(self):
			while True:
				s = input(">>> ")
				
	CLI()
