"""
https://manga.bilibili.com/detail/mc25940
"""

import json
import re
import io
from urllib.parse import urljoin
from zipfile import ZipFile

from deno_vm import VM

from ..core import Episode
from ..grabber import grabhtml

domain = ["manga.bilibili.com"]
name = "manga.bilibili"

class ComicDetail(dict):
	def load(self, id):
		result = grabhtml(
			"https://manga.bilibili.com/twirp/comic.v2.Comic/ComicDetail?device=pc&platform=web",
			method="POST",
			json={"comic_id": id}
			)
		result = json.loads(result)
		self[id] = result

comic_detail = ComicDetail()

class Decoder:
	def __init__(self):
		self.vm = None

	def loaded(self):
		return bool(self.vm)

	def load(self, bili_js_url):
		bili_js = grabhtml(bili_js_url)
		js = """
		const window = {};
		const self = window;
		""" + bili_js + """
		let decode;
		let factory;
		let webpack;
		for (const key in window) {
			if (key.startsWith("webpack")) {
				webpack = window[key];
			}
		}
		for (const fn of Object.values(webpack[0][1])) {
		  if (fn.toString().includes('Indexer')) {
			factory = fn;
			break;
		  }
		}
		const _require = () => ({
		  async loadAsync(data) {
			throw {
			  data,
			  message: 'extract data'
			};
		  }
		});
		_require.d = (exports, o) => {
		  const getValue = Object.values(o)[0];
		  decode = getValue();
		};

		factory({}, {}, _require);

		var exportDecode = (seasonId, episodeId, data) => {
		  return decode(seasonId, episodeId, (data))
			.catch(err => {
				if (err.message !== "extract data") throw err;
				return Array.from(err.data);
			});
		};
		"""
		# import pathlib
		# pathlib.Path("bili.js").write_text(js, encoding="utf8")
		self.vm = VM(js)
		self.vm.create()

	def decode(self, id, ep_id, data):
		return bytes(self.vm.call('exportDecode', id, ep_id, list(data)))

decoder = Decoder()

def get_title(html, url):
	id = int(re.search(r'mc(\d+)', url).group(1))
	if id not in comic_detail:
		comic_detail.load(id)
	return comic_detail[id]["data"]["title"]

def get_episodes(html, url):
	id = int(re.search(r'mc(\d+)', url).group(1))
	if id not in comic_detail:
		comic_detail.load(id)
	detail = comic_detail.pop(id)
	return [Episode(
		"{} - {}".format(ep["short_title"], ep["title"]),
		urljoin(url, "/mc{}/{}?from=manga_detail".format(id, ep["id"]))
		) for ep in reversed(detail["data"]["ep_list"])]

def get_images(html, url):
	_id, ep_id = (int(n) for n in re.search(r'mc(\d+)/(\d+)', url).groups())
	if not decoder.loaded():
		bili_js = re.search(r'src="([^"]+/bili\.\w+\.js)', html).group(1)
		decoder.load(urljoin(url, bili_js))
	image_index = grabhtml(
		"https://manga.bilibili.com/twirp/comic.v1.Comic/GetImageIndex?device=pc&platform=web",
		method="POST",
		json={"ep_id": ep_id}
		)
	image_index = json.loads(image_index)
	# image_index_url = urljoin(image_index["data"]["host"], image_index["data"]["path"])
	# image_index_file = grabber(image_index_url).content
	# image_index_file = decoder.decode(id, ep_id, image_index_file)
	# index = read_zip(image_index_file, "index.dat")
	# index = json.loads(index)
	return [ImageGetter(i["path"], referer=url) for i in image_index["data"]["images"]]

def read_zip(b, filename):
	with ZipFile(io.BytesIO(b)) as zip:
		return zip.read(filename).decode("utf8")

class ImageGetter:
	def __init__(self, path, **kwargs):
		self.path = path
		self.kwargs = kwargs

	def __call__(self):
		result = grabhtml(
			"https://manga.bilibili.com/twirp/comic.v1.Comic/ImageToken?device=pc&platform=web",
			method="POST",
			json={"urls": json.dumps([self.path])},
			**self.kwargs
			)
		result = json.loads(result)
		return "{}?token={}".format(result["data"][0]["url"], result["data"][0]["token"])

