from .util import url_extract_filename

class Image:
	"""Image container"""
	def __init__(self, url=None, get_url=None, data=None, filename=None):
		self.url = url
		self.get_url = get_url
		self.data = data
		self.filename = filename
		self.static_filename = bool(filename)
		
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
			
		return Image(data=data)
