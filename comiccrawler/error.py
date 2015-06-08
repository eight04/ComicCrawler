class ComicCrawlerError(BaseException): pass

class LastPageError(ComicCrawlerError): pass

class SkipEpisodeError(ComicCrawlerError): pass

class PauseDownloadError(ComicCrawlerError): pass

class ImageExistsError(ComicCrawlerError): pass
