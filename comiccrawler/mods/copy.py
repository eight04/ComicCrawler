#! python3
"""
https://copymanga.com/comic/bulunshitang

"""

import re
import json
from html import unescape

from Cryptodome.Cipher import AES
from Cryptodome.Util.Padding import unpad

from ..episode import Episode
from ..grabber import grabhtml
from ..url import urljoin

domain = ["copymanga.com"]
name = "拷貝"

def get_title(html, url):
	return unescape(re.search("<h6[^>]*>([^<]+)", html).group(1)).strip()
	
def extract_data(html, data=None):
	if not data:
		try:
			data = re.search('class="disposableData"\s+disposable="([^"]+)', html).group(1)
		except AttributeError:
			data = re.search('class="disData"\s+contentKey="([^"]+)', html).group(1)	
			
	try:
		pa = re.search('class="disposablePass"\s+disposable="([^"]+)', html).group(1)
	except AttributeError:
		pa = re.search('class="disPass"\s+contentKey="([^"]+)', html).group(1)
		
	pa = pa.encode("utf8")
	iv = data[:16].encode("utf8")
	
	cipher = AES.new(pa, AES.MODE_CBC, iv=iv)
	result = unpad(cipher.decrypt(bytes.fromhex(data[16:])), AES.block_size).decode("utf8")
	return json.loads(result)
	

def get_episodes(html, url):
	cid = re.search("[^/]+$", url).group()
	data = json.loads(grabhtml(urljoin(url, f"/comicdetail/{cid}/chapters")))["results"]
	data = extract_data(html, data)
	for group in data["groups"].values():
		for chapter in group["chapters"]:
			yield Episode(
				title=chapter["name"],
				url=f"{url}/chapter/{chapter['id']}"
			)
	
def get_images(html, url):
	data = extract_data(html)
	return [i["url"] for i in data]
	