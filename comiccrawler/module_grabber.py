from requests.utils import dict_from_cookiejar

from .grabber import grabhtml, grabimg

def purify_cookie(cookie):
	"""Remove empty cookie value."""
	return {key: value for key, value in cookie.items() if value and "請" not in value}

class ModuleGrabber:
	"""Bind grabber with module's header, cookie..."""
	def __init__(self, mod):
		self.mod = mod
		
	def html(self, url, **kwargs):
		return self.grab(grabhtml, url, **kwargs)
		
	def img(self, url, **kwargs):
		return self.grab(grabimg, url, **kwargs)
		
	def grab(self, grab_method, url=None, **kwargs):
		new_kwargs = {
			"header": self.get_header(),
			"cookie": purify_cookie(self.get_cookie()),
			"done": self.handle_grab,
			"proxy": self.mod.config.get("proxy"),
			"verify": self.mod.config.getboolean("verify", True)
			}
		new_kwargs.update(kwargs)
		
		if hasattr(self.mod, "grabhandler"):
			result = self.mod.grabhandler(grab_method, url, **new_kwargs)
			if result:
				return result
		return grab_method(url, **new_kwargs)
		
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
