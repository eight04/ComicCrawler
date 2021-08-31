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

domain = ["copymanga.com"]
name = "拷貝"

def get_title(html, url):
	return unescape(re.search("<h6[^>]*>([^<]+)", html).group(1)).strip()
	
def extract_data(html):
	data = re.search('class="disposableData"\s+disposable="([^"]+)', html).group(1)
	pa = re.search('class="disposablePass"\s+disposable="([^"]+)', html).group(1).encode("utf8")
	iv = data[:16].encode("utf8")
	
	cipher = AES.new(pa, AES.MODE_CBC, iv=iv)
	result = unpad(cipher.decrypt(bytes.fromhex(data[16:])), AES.block_size).decode("utf8")
	return json.loads(result)
	

def get_episodes(html, url):
	data = extract_data(html)
	for group in data["default"]["groups"].values():
		for chapter in group:
			yield Episode(
				title=chapter["name"],
				url=f"{url}/chapter/{chapter['uuid']}"
			)
	
def get_images(html, url):
	data = extract_data(html)
	return [i["url"] for i in data]
	