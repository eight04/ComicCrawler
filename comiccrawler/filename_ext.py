from email.message import EmailMessage
from urllib.parse import urlsplit
from pathlib import Path
import re

import puremagic

mime_dict = {
	t.mime_type: t for t in puremagic.magic_header_array
	}

def ext_from_mime(mime):
	mime = mime.lower().strip()
	try:
		return mime_dict[mime].extension
	except KeyError:
		return None

def ext_from_url(url):
	path = urlsplit(url).path
	if "." in path:
		return Path(path).suffix
	return None

def ext_from_disposition(r):
	msg = EmailMessage()
	for key, value in r.headers.items():
		msg.add_header(key, value)
	filename = msg.get_filename()
	if not filename:
		return None
	return Path(filename).suffix

def ext_from_peek(b):
	# imghdr issue: http://bugs.python.org/issue16512
	if b[:2] == b"\xff\xd8":
		return ".jpg"

	# http://www.garykessler.net/library/file_sigs.html
	if b[:4] == b"\x1a\x45\xdf\xa3":
		return ".webm"

	if b[:4] == b"RIFF" and b[8:12] == b"WEBP":
		return ".webp"

	if b[:4] == b"8BPS":
		return ".psd"

	if (b[:16] == b"\x30\x26\xB2\x75\x8E\x66\xCF\x11"
	 b"\xA6\xD9\x00\xAA\x00\x62\xCE\x6C"):
		return ".wmv"

def _get_ext(r, b, tempfile):
	"""Get file extension"""
	if b and (ext := ext_from_peek(b)):
		return ext

	if ext := ext_from_disposition(r):
		return ext

	mime = None
	if "Content-Type" in r.headers:
		mime = re.search("^(.*?)(;|$)", r.headers["Content-Type"]).group(1)
		mime = mime.strip()
		if "octet-stream" in mime:
			mime = None

	if mime:
		ext = ext_from_mime(mime)
		if ext:
			return ext

		# FIXME: is it safe to handle x-? like this?
		# video/x-m4v
		match = re.match(r"\w+/x-(\w+)$", mime)
		if match:
			return f".{match.group(1)}"

	if r and (ext := ext_from_url(r.url)):
		return ext

	if b:
		filename = urlsplit(r.url).path
		return puremagic.from_string(b, filename=filename)

	if tempfile:
		return puremagic.from_file(tempfile)


def get_ext(r, b, tempfile):
	"""Get file extension"""
	ext = _get_ext(r, b, tempfile)
	# some mapping
	if ext in (".jpeg", ".jpe"):
		return ".jpg"
	# https://github.com/cdgriffith/puremagic/issues/3
	if ext == ".docx":
		return ".zip"
	return ext

