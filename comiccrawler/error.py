class ComicCrawlerSignal(BaseException):
	"""Extend BaseException."""
	pass

class LastPageError(ComicCrawlerSignal):
	"""Raise LastPageError to exit crawl pages loop."""
	pass

class SkipEpisodeError(ComicCrawlerSignal):
	"""Raise SkipEpisodeError to exit crawl episodes loop."""
	pass

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
