#! python3

# pylint: disable=unused-import
from collections.abc import Callable
from urllib.parse import urlparse, urlunparse, parse_qs, urlencode, urljoin

URL_PARTS = ("scheme", "netloc", "path", "params", "query", "fragment")

def urlextract(url):
	result = urlparse(url)
	dict = {}
	for prop in URL_PARTS:
		dict[prop] = getattr(result, prop)
	return dict
	
def urlbuild(d):
	return urlunparse(d.get(p) for p in URL_PARTS)

def urlupdate(url, **parts):
	d = urlextract(url)
	d.update(parts)
	return urlbuild(d)
	
def update_qs(url, new_query: dict[str, str | Callable[[str], str]]):
	d = urlextract(url)
	query_dict = parse_qs(d["query"])
	for key, value in new_query.items():
		if callable(value):
			value = value(query_dict.get(key, "")[0])
		if value is None:
			query_dict.pop(key, None)
		else:
			query_dict[key] = [value]
	d["query"] = urlencode(query_dict, doseq=True)
	return urlbuild(d)
