from requests import HTTPError

class ComicCrawlerSignal(BaseException):
	"""Extend BaseException."""
	pass

class LastPageError(ComicCrawlerSignal):
	"""Raise LastPageError to exit crawl pages loop."""
	pass

class SkipEpisodeError(ComicCrawlerSignal):
	"""Raise SkipEpisodeError to exit crawl episodes loop."""
	def __init__(self, always=True):
		super().__init__()
		self.always = always

class PauseDownloadError(ComicCrawlerSignal):
	"""Raise PauseDownloadError to exit crawl mission loop."""
	pass
	
class SkipPageError(ComicCrawlerSignal):
	"""Raise this error to skip a page in the analyzer."""
	pass

# class ExitErrorLoop(ComicCrawlerSignal):
	# """Raise ExitErrorLoop to exit error loop."""
	# pass

class ComicCrawlerError(Exception):
	"""Extend Exception."""
	pass

class ModuleError(ComicCrawlerError):
	"""Can't find module."""
	pass

def is_403(err):
	return is_http(err, code=403)
	
def is_http(err, code=None):
	if not isinstance(err, HTTPError):
		return False
		
	if code is None:
		return True
		
	try:
		if err.response.status_code == code:
			return True
	except AttributeError:
		pass
		
	return False
