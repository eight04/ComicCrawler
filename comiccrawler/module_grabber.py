from requests.utils import dict_from_cookiejar

from .core.grabber import grabhtml, grabimg

class ModuleGrabber:
	"""Bind grabber with module's header, cookie..."""
	def __init__(self, mod):
		self.mod = mod
		
	def html(self, url, **kwargs):
		return grabhtml(
			url,
			header=self.get_header(),
			cookie=self.get_cookie(),
			done=self.handle_grab,
			proxy=self.mod.config.get("proxy"),
			**kwargs
		)
	
	def img(self, url, **kwargs):
		return grabimg(
			url,
			header=self.get_header(),
			cookie=self.get_cookie(),
			done=self.handle_grab,
			proxy=self.mod.config.get("proxy"),
			**kwargs
		)
		
	def get_header(self):
		"""Return downloader header."""
		return getattr(self.mod, "header", None)

	def get_cookie(self):
		"""Return downloader cookie."""
		cookie = getattr(self.mod, "cookie", {})
		config = getattr(self.mod, "config", {})
		
		for key, value in config.items():
			if key.startswith("cookie_"):
				name = key[7:]
				cookie[name] = value
				
		return cookie
		
	def handle_grab(self, session, _response):
		cookie = dict_from_cookiejar(session.cookies)
		config = getattr(self.mod, "config", None)
		if not config:
			return
			
		for key in config:
			if key.startswith("cookie_"):
				name = key[7:]
				if name in cookie:
					config[key] = cookie[name]
