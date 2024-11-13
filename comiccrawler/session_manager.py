from urllib.parse import urlparse
from threading import Lock
from typing import Callable, Any

from requests import Session as RequestsSession

from .util import extract_curl

default_header = {
	"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0",
	# "Accept-Language": "zh-tw,zh;q=0.8,en-us;q=0.5,en;q=0.3",
	# "Accept-Encoding": "gzip, deflate"
	}

def default_key(url: str) -> tuple:
	r = urlparse(url)
	return (r.scheme, r.netloc)

class Session(RequestsSession):
	timeout: Any = (22, 60)

	def request(self, *args, **kwargs):
		if "timeout" not in kwargs:
			kwargs["timeout"] = self.timeout
		return super().request(*args, **kwargs)

class SessionManager:
	def __init__(self) -> None:
		self.lock = Lock()
		self.default_jar = None
		self.sessions: dict[Any, Session] = {}
		self.session_keys: list[Callable[[str], tuple | None]] = [default_key]

	def get(self, url: str) -> Session:
		with self.lock:
			key = None
			for key_fn in self.session_keys:
				if key := key_fn(url):
					break
			else:
				raise KeyError(f"No key found for url: {url}")

			if key not in self.sessions:
				self.sessions[key] = Session()
				self.sessions[key].headers.update(default_header)
				if self.default_jar:
					# FIXME: do we have to check cookies' domain?
					self.sessions[key].cookies.update(self.default_jar)

			return self.sessions[key]

	def add_session_key(self, key_fn: Callable[[str], tuple | None]) -> None:
		with self.lock:
			self.session_keys.insert(0, key_fn)

	def update_by_curl(self, curl: str) -> None:
		url, headers, cookies = extract_curl(curl)
		session = self.get(url)
		with self.lock:
			session.headers.update(headers)
			session.cookies.update(cookies)

	def set_default_cookie(self, jar) -> None:
		self.default_jar = jar


session_manager = SessionManager()
