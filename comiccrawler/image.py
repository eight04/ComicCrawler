from .util import url_extract_filename

class Image:
	"""Image container"""
	def __init__(self, url=None, get_url=None, data=None, filename=None, ext=None, static_filename=None):
		self.url = url
		self.get_url = get_url
		self.data = data
		self.filename = filename
		if static_filename is None:
			self.static_filename = bool(filename)
		else:
			self.static_filename = static_filename
		self.ext = ext
		
		if not filename and url:
			self.filename = url_extract_filename(url)
			
	def resolve(self):
		if not self.url and self.get_url:
			self.url = self.get_url()
		
		if not self.filename and self.url:
			self.filename = url_extract_filename(self.url)
	
	@classmethod
	def create(cls, data):
		if isinstance(data, Image):
			return data
			
		if isinstance(data, str):
			return Image(url=data)
			
		if callable(data):
			return Image(get_url=data)

		if isinstance(data, dict):
			return Image(**data)
			
		return Image(data=data)
