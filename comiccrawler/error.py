class ComicCrawlerSignal(BaseException):
	"""Extend BaseException."""
	pass

class LastPageError(ComicCrawlerSignal):
	"""Raise LastPageError to exit crawl pages loop."""
	pass

class SkipEpisodeError(ComicCrawlerSignal):
	"""Raise SkipEpisodeError to exit crawl episodes loop."""
	def __init__(self, always=True):
		self.aways = always

class PauseDownloadError(ComicCrawlerSignal):
	"""Raise PauseDownloadError to exit crawl mission loop."""
	pass

class ExitErrorLoop(ComicCrawlerSignal):
	"""Raise ExitErrorLoop to exit error loop."""
	pass

class ComicCrawlerError(Exception):
	"""Extend Exception."""
	pass

class ModuleError(ComicCrawlerError):
	"""Can't find module."""
	pass
