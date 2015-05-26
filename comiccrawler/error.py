class CrawlerError(BaseException): pass

class MissionDuplicateError(CrawlerError): pass

class ImageExistsError(CrawlerError): pass

class LastPageError(CrawlerError): pass

class TooManyRetryError(CrawlerError): pass

class EmptyImageError(CrawlerError): pass

class SkipEpisodeError(CrawlerError): pass

class AccountError(CrawlerError): pass
