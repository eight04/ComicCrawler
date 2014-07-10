#! python3

import imghdr

# imghdr issue: http://bugs.python.org/issue16512
def _test_jpeg(h, f):
	if h[:2] == b"\xff\xd8":
		return "JPEG"
	return None
imghdr.tests.append(_test_jpeg)

def _test_swf(h, f):
	if h[:3] == b"CWS" or h[:3] == b"FWS":
		return "SWF"
	return None
imghdr.tests.append(_test_swf)

def _test_psd(h, f):
	if h[:4] == b"8BPS":
		return "PSD"
	return None
imghdr.tests.append(_test_psd)

def _test_rar(h, f):
	if h[:7] == b"Rar!\x1a\x07\x00":
		return "RAR"
	return None
imghdr.tests.append(_test_rar)

from safeprint import safeprint

INIT = 0
ANALYZED = 1
DOWNLOADING = 2
PAUSE = 3
FINISHED = 4
ERROR = 5
INTERRUPT = 6
UPDATE = 7

_eventhandler = None
def _evtcallback(msg, *arg):
	"""GUI Message control"""
	
	if callable(_eventhandler):
		_eventhandler(msg, *arg)
	
"""
def getimgext(url):
	url = url.lower()
	if ".png" in url:
		return "png"
	if ".gif" in url:
		return "gif"
	if ".swf" in url:
		return "swf"
	if ".psd" in url:
		return "psd"
	if ".rar" in url:
		return "rar"
	return "jpg"
"""

def getext(byte):
	"""Test the file type according byte stream with imghdr"""
	
	r = imghdr.what("", byte)
	if not r:
		return None
		
	if r.lower() == "jpeg":
		return "jpg"
	return r.lower()
			
def createdir(path):
	"""Create folder of filepath. 
	
	This function can handle sub-folder like 
	"this_doesnt_exist\sure_this_doesnt_exist_either\I_want_to_create_this"
	
	"""
	
	dirpath = path.split("\\")
	create = ""
	for d in dirpath:
		create += d + "\\"
		try:
			os.mkdir(create)
		except Exception as er:
			_evtcallback("MAKEDIR_EXC", er)

def safefilepath(s):
	"""Return a safe dir name. Return string."""

	return re.sub("[/\\\?\|<>:\"\*]","_",s).strip()
	
def safeurl(url):
	"""Return a safe url, quote the unicode characters."""
	
	base = re.search("(https?://[^/]+)", url).group(1)
	path = url.replace(base, "")
	def u(match):
		return urllib.parse.quote(match.group())
	path = re.sub("[\u0080-\uffff]+", u, path)
	return base + path
	
def grabhtml(url, hd={}, encode=None):
	"""Get html source of given url. Return String."""
	
	url = safeurl(url)
	req = urllib.request.Request(url,headers=hd)
	rs = urllib.request.urlopen(req, timeout=20)
	ot = rs.read()
	
	# auto cookie controler
	"""
	from http.cookies import SimpleCookie
	c = SimpleCookie()
	
	try:
		c.load(hd["Cookie"])
	except Exception:
		pass
	try:
		c.load(rs.getheader("Set-Cookie"))
	except Exception:
		pass
	cookie = ""
	for k in c:
		cookie += "{}={};".format(k, c[k].value)
	hd["Cookie"] = cookie
	"""
	
	if encode is None:
		try:
			encode = re.search("<meta charset=(\"|')([^\"']+)(\"|')").group(2)
			return ot.decode(encode, "replace")
		except Exception:
			pass
		try:
			encode = re.search("charset=([^\"'>]+)",ot.decode("utf-8","replace")).group(1)
			return ot.decode(encode, "replace")
		except Exception:
			return ot.decode("utf-8", "replace")
	else:
		return ot.decode(encode,"replace")

def grabimg(url, hd={}):
	"""Return byte stream."""
	
	url = safeurl(url)
	req = urllib.request.Request(url, headers=hd)
	rs = urllib.request.urlopen(req, timeout=20)
	return rs.read()

class Mission:
	"""Mission data class. Contains a mission's information."""
	
	def __init__(self):
		self.title = ""
		self.url = ""
		self.episodelist = []
		self.state = INIT
		# self.statechangecallback = None
		self.downloader = None
		self.lock = threading.Lock()
		
	def state_(self, state=None):
		if not state:
			return self.state
		self.state = state
		_evtcallback("MISSION_STATE_CHANGE", self)
			
	def __getstate__(self):
		state = self.__dict__.copy()
		del state["downloader"]
		del state["lock"]
		# if "statechangecallback" in state:
			# del state["statechangecallback"]
		return state
		
	def __setstate__(self, state):
		self.__dict__.update(state)
		self.lock = threading.Lock()
		
	def setTitle(self, title):
		self.title = title
		_evtcallback("MISSION_TITLE_CHANGE", self)

class Episode:
	"""Episode data class. Contains a book's information."""
	
	def __init__(self):
		self.title = ""
		self.firstpageurl = ""
		self.currentpageurl = ""
		self.currentpagenumber = 0
		self.skip = False
		self.complete = False
		self.error = False
		self.errorpages = 0
		self.totalpages = 0


class DownloadWorker:
	def __init__(self, crawler):
	
		def worker():
			while True:
				mission = crawler.missionque.take()
				# print(mission)
				if mission is None:
					crawler.stop()
					safeprint("All download complete!")
					break
					
				try:
					mission.lock.acquire()
					mission.state_(DOWNLOADING)
					self.download(mission)
				except (ExitSignalError, InterruptError):
					print("kill download worker")
					mission.state_(PAUSE)
				except TooManyRetryError:
					safeprint("Too many retry")
					mission.state_(PAUSE)
					crawler.missionque.drop((mission,))
				except Exception as er:
					import traceback
					er_message = traceback.format_exc()
					print("worker terminate!\n{}".format(er_message))
					crawler.stop()
					mission.state_(ERROR)
					_evtcallback("WORKER_TERMINATED", mission, er, er_message)
				finally:
					mission.lock.release()
					
				if self._stop:
					# safeprint("Download worker killed.")
					break
		
		self._stop = False
		self.savepath = crawler.savepath.rstrip("\\/")
		self.threading = threading.Thread(target=worker)
		self.crawler = crawler
		
		self.threading.start()

	def download(self, mission):
		"""Start mission download. This method will call self.crawlpage()
		for each episode.
		
		"""
		
		safeprint("total {} episode.".format(len(mission.episodelist)))
		for ep in mission.episodelist:
			if ep.skip or ep.complete:
				continue
				
			# deside wether to generate Episode folder, or it will put every 
			# image file in one folder. Ex. pixiv.net
			if ("noepfolder" in mission.downloader.__dict__ and 
					mission.downloader.noepfolder):
				efd = "{}\\{}\\".format(self.savepath, safefilepath(mission.title))
				fexp = safefilepath(ep.title) + "_{:03}"
			else:
				efd = "{}\\{}\\{}\\".format(self.savepath, safefilepath(mission.title), safefilepath(ep.title))
				fexp = "{:03}"
			createdir(efd)
			
			safeprint("Downloading ep {}".format(ep.title))
			try:
				self.crawlpage(ep, efd, mission, fexp)
			except LastPageError:
				safeprint("Episode download complete!")
				print("")
				ep.complete = True
				self.crawler.save()
				"""
			except InterruptError:
				safeprint("Download interrupted.")
				mission.state_(PAUSE)
				self.crawler.save()
				break
				"""
		else:
			safeprint("Mission complete!")
			mission.state_(FINISHED)
			
			# run after download
			command = self.crawler.runafterdownload
			if not command:
				return
			try:
				import subprocess
				subprocess.call((command, "{}/{}".format(self.savepath, safefilepath(mission.title))))
			except Exception as er:
				safeprint("failed to run process: {}".format(er))

	def crawlpage(self, ep, savepath, mission, fexp):
		"""Crawl all pages of an episode.
		
		Grab image into savepath. To exit the method, raise LastPageError.
		
		Should define error handler for grabimg failed. Note the error by
		setting episode.errorpages, episode.currentpagenumber, episode.
		totalpages, episode.currentpageurl.
		
		"""
		
		downloader = mission.downloader
		
		if not ep.currentpagenumber:
			ep.currentpagenumber = 1
		if not ep.currentpageurl:
			ep.currentpageurl = ep.firstpageurl
			
		imgurls = None
		if "getimgurls" in downloader.__dict__:
			# we can get all img urls from first page
			errorcount = 0
			while not imgurls:
				try:
					html = grabhtml(ep.firstpageurl, hd=downloader.header)
					imgurls = downloader.getimgurls(html, url=ep.firstpageurl)
				except Exception as er:
					safeprint("get imgurls failed: {}".format(er))
					# import traceback
					# print(traceback.format_exc())
					errorcount += 1
					if errorcount >= 10:
						# self.crawler.missionque.drop((mission, ))
						raise TooManyRetryError
					if "errorhandler" in downloader.__dict__:
						downloader.errorhandler(er, ep)
					self.pausecallback(mission)
					time.sleep(5)
		ep.imgurls = imgurls
		
		# downloaded list for later use
		import os
		downloadedlist = [ i.rpartition(".")[0] for i in os.listdir(savepath) ]
		
		# crawl all pages
		errorcount = 0
		while True:
			safeprint("Crawling {} {} page {}...".format(mission.title, 
					ep.title, ep.currentpagenumber))
			try:
				if not imgurls:
					# getimgurl method
					html = grabhtml(ep.currentpageurl, hd=downloader.header)
					
					imgurl = downloader.getimgurl(html, 
							page=ep.currentpagenumber, url=ep.currentpageurl)
					nextpageurl = downloader.getnextpageurl(ep.currentpagenumber, 
							html, url=ep.currentpageurl)
					try:
						imgurl, header = imgurl
					except Exception:
						header = downloader.header
				else:
					# getimgurls method
					imgurl = imgurls[ep.currentpagenumber - 1]
					header = downloader.header
					nextpageurl = ep.currentpagenumber < len(imgurls)
				
				# generate file name
				# ext = getimgext(imgurl)
				fn = fexp.format(ep.currentpagenumber)
				
				# file already exist
				if fn in downloadedlist:
					raise FileExistError
					
				safeprint("Downloading image: {}".format(imgurl))
				oi = grabimg(imgurl,hd=header)
				
				# check image type
				ext = getext(oi)
				if not ext:
					raise Exception("Invalid image type.")
					
			except FileExistError:
				safeprint("...page {} already exist".format(
						ep.currentpagenumber))
						
			except Exception as er:
				safeprint("Crawl page error: {}".format(er or type(er)))
				errorcount += 1
				if errorcount >= 10:
					# self.crawler.missionque.drop((mission, ))
					raise TooManyRetryError
				self.pausecallback(mission)
				
				if not downloader.errorhandler(er, ep):
					time.sleep(5)
				continue
				
			else:
				# everything is ok, save image
				f = open(savepath + fn + "." + ext, "wb")
				f.write(oi)
				f.close()
				
			# call pause
			self.pausecallback(mission)
				
			if not nextpageurl:
				ep.complete = True
				raise LastPageError
			ep.currentpageurl = nextpageurl
			ep.currentpagenumber += 1
			errorcount = 0
			print("")
	
	def stop(self):
		self._stop = True
		
	def pausecallback(self, mission=None):
		"""Hook to stop worker thread."""		
		if self._stop:
			raise InterruptError
			
	def join(self):
		"""thread join method."""
		self.threading.join()

		
class AnalyzeWorker:
	def __init__(self, mission, callback=None):
		self.mission = mission
		self.callback = callback
		self._stop = False
		self.threading = threading.Thread(target=self.worker)
		
		self.threading.start()
	
	def worker(self):
		try:
			self.analyze(self.mission)
		except Exception as er:
			# safeprint("Analyzed failed: {}".format(er))
			mission.state = ERROR
			self.callback(self.mission, er)
		else:
			mission.state = ANALYZED
			self.callback(self.mission)

	def analyze(self):
		"""Analyze mission url."""
		mission = self.mission
		
		safeprint("start analyzing {}".format(mission.url))
		
		downloader = mission.downloader
		html = grabhtml(mission.url, hd=downloader.header)
		# print(html)
		
		mission.title = downloader.gettitle(html, url=mission.url)
		epList = downloader.getepisodelist(html, url=mission.url)
		if not mission.episodeList:
			mission.episodeList = epList
		else:
			for ep in epList:
				for oep in mission.episodeList:
					if oep.url == ep.url:
						break
				else:
					mission.episodeList.append(ep)
					mission.update = True
			if not mission.update:
				return

		if not mission.episodelist:
			raise Exception("get episode list failed!")
		
		safeprint("analyzed succeed!")
		if mission.update:
			mission.state_(UPDATE)
		else:
			mission.state = ANALYZED
	
	def stop(self):
		"""not working with analyze"""
		self._stop = True
			
	def join(self):
		"""thread join method."""
		self.threading.join()
