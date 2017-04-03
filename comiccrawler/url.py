#! python3

# pylint: disable=unused-import
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
	
def update_qs(url, new_query):
	d = urlextract(url)
	query_dict = parse_qs(d["query"])
	query_dict.update(new_query)
	d["query"] = urlencode(query_dict, doseq=True)
	return urlbuild(d)
