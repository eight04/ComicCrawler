class Episode:
	"""Create Episode object. Contains information of an episode."""
	def __init__(self, title=None, url=None, current_url=None, current_page=0,
			skip=False, complete=False, total=0, image=None):
		"""Construct."""
		self.title = title
		self.url = url
		self.current_url = current_url
		# position of images on current page
		self.current_page = current_page
		self.skip = skip
		self.complete = complete
		# total number of images in this episode
		self.total = total
		self.image = image
