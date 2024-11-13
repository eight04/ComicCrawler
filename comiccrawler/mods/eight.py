#! python3

"""this is 8comic module for comiccrawler.
	
http://www.comicbus.com/html/197.html

"""

import re
from urllib.parse import urljoin

from deno_vm import VM, eval

from ..core import Episode, grabhtml
from ..util import clean_tags

domain = ["8comic.com", "www.comicvip.com", "comicbus.com", "www.comicabc.com"]
name = "無限"
next_page_cache = {}
nview = None

def get_title(html, url):
	return re.search(r'addhistory\("\d+","([^"]+)',html).group(1)

def get_episodes(html, url):
	html = html.replace("\n", "")
	
	comicview_js = grabhtml(urljoin(url, "/js/comicview.js"))
	js = """
	function cview(...args) {
		var output;
		function getCookie() {}
		function getcookie() {}
		var window = {
			open: function(result){
				output = result;
			}
		};
		const location = {set href(url) {output = url;}};
		const document = {location};
		const $ = () => $;
		$.attr = $.html = $.text = $;
		const addch = () => {};
		""" + comicview_js + """
		cview(...args);
		return output;
	}
	"""

	s = []
	matches = re.finditer(
		r'<a [^>]*?onclick="(cview[^"]+?);[^>]*>(.+?)</a>',
		html, re.M
	)
	with VM() as vm:
		vm.run(js)
		for match in matches:
			cview, title = match.groups()
			if "this" in cview:
				continue

			ep_url = vm.run(cview)
			# ep_url = vm.run("location.href")
			title = clean_tags(title)

			e = Episode(title, urljoin(url, ep_url))
			s.append(e)
	return s

j_js = ""
lazy_js = ""
	
def get_images(html, url):
	global j_js
	if not j_js:
		j_js = re.search(r'src="([^"]*/j\.js[^"]*)"', html).group(1)
		j_js = urljoin(url, j_js)
		j_js = grabhtml(j_js)
	
	script = re.search('(function request.+?)</script>', html, re.DOTALL).group(1)

	global lazy_js
	if not lazy_js:
		try:
			lazy_js = re.search(r'src="([^"]*/lazyloadx\.js[^"]*)"', html).group(1)
		except AttributeError:
			pass
		else:
			lazy_js = urljoin(url, lazy_js)
			lazy_js = grabhtml(lazy_js)
			lazy_js = re.search(r'(var a=[\s\S]*?)o\.setAttribute', lazy_js).group(1)
	
	js = """
(() => {
var url = """ + f"{url!r}" + """,
  images = [],
  document = {
    documentElement: {},
    location: {
      toString() {
        return url;
      },
      get href() {
        return url;
      },
      set href(_url) {
        url = _url;
      },
    },
    getElementById() {
      return {
        set src(value) {
          images.push(value);
        },
        style: {},
      };
    },
	images: []
  },
  navigator = {
    userAgent: "",
    language: "",
  },
  window = { location: document.location,
  document},
  alert = () => {},
  localStorage = {
    getItem() {
      return null;
    },
    setItem() {},
  },
  $ = () => $,
  ps,
  ci,
  pi,
  ni,
  vv = "",
  src;
$.attr = $.ready = $.on = $.click = $.hide = $.show = $.css = $.html = $.append = $.get = $.ajax = $.post = $;

""" + j_js + script + """
		
function *parseSrc() {
  const rx = / s="([^"]+)"/g;
  while ((m = rx.exec(xx))) {
    yield m[1];
  }
}

return [...parseSrc()].map(src => {
	""" + lazy_js + """
	return unescape(src)
});

})();
"""
	# import pathlib
	# pathlib.Path("8comic.js").write_text(js)
	imgs = eval(js)
	return [urljoin(url, img) for img in imgs]

