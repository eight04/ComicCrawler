class ComicCrawlerSignal(BaseException): pass

class LastPageError(ComicCrawlerSignal): pass

class SkipEpisodeError(ComicCrawlerSignal): pass

class PauseDownloadError(ComicCrawlerSignal): pass

class ImageExistsError(ComicCrawlerSignal): pass

class ComicCrawlerError(Exception): pass

class ModuleError(ComicCrawlerError): pass
