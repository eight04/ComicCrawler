#! python3

"""Simple io module depressing exceptions"""

import io
import os
from os import path
import pprint
import glob
import time
import shutil
import json
from contextlib import contextmanager, suppress

CHUNK_LIMIT = 500 * 1000 * 1000

def write_big(file, content):
	for piece in range(0, len(content), CHUNK_LIMIT):
		file.write(content[piece:piece + CHUNK_LIMIT])

def exists(file):
	file = path.expanduser(file)
	
	return path.exists(file)

def is_file(file):
	"""Check if the file is file."""
	file = path.expanduser(file)

	return path.isfile(file)

def content_write(file, content, append=False):
	"""Write content to file. Content may be str or bytes."""
	file = path.expanduser(file)

	prepare_folder(path.dirname(file))

	original = file

	if append:
		mode = "a"
	else:
		mode = "w"
		file = file + time.strftime("@%Y-%m-%d_%H%M%S")

	if isinstance(content, bytes):
		mode += "b"
		with io.open(file, mode) as f:
			write_big(f, content)

	else:
		if not isinstance(content, str):
			content = pprint.pformat(content)

		with io.open(file, mode, encoding="utf-8") as f:
			write_big(f, content)

	if file != original:
		os.replace(file, original)

def content_read(file, raw=False):
	"""Read content from file. Return str."""
	file = path.expanduser(file)

	if not path.isfile(file):
		return ""

	if raw:
		with io.open(file, "rb") as f:
			return f.read()
	else:
		with io.open(file, "r", encoding="utf-8-sig") as f:
			return f.read()

def prepare_folder(folder):
	"""If the folder does not exist, create it."""
	folder = path.expanduser(folder)

	if not path.isdir(folder):
		os.makedirs(folder)

	return folder

def prepare_file(file):
	"""If the file does not exist, create it."""
	file = path.expanduser(file)

	prepare_folder(path.dirname(file))

	if not path.isfile(file):
		with io.open(file, "w", encoding="utf8"):
			pass

	return file
	
def move(src, dest):
	"""Move src files to dest. Should support wildcard."""
	src = path.expanduser(src)
	dest = path.expanduser(dest)

	if "*" in src:
		# Wildcard multiple move
		prepare_folder(dest)

		for file in glob.iglob(src):
			os.rename(file, path.join(dest, path.basename(file)))
	else:
		# just a rename
		if not exists(src):
			return

		prepare_folder(path.dirname(dest))
		os.rename(src, dest)

def backup(arg):
	"""Create backup file.
	
	:param arg: str - glob pattern or filename.
	"""
	arg = path.expanduser(arg)
	if "*" in arg:
		# Wildcard multiple copy
		for file in glob.iglob(arg):
			shutil.copyfile(file, file + time.strftime("@%Y-%m-%d_%H%M%S"))
	else:
		if not is_file(arg):
			return
		shutil.copyfile(arg, arg + time.strftime("@%Y-%m-%d_%H%M%S"))

def path_each(folder, callback, mode="f"):
	"""Iter through all file in the folder.

	`folder` may contain "*", or it will use the children in the folder.
	`callback` will recieve a filename param.
	`mode` is a string containing f or/and d, to filter file, directory.
	"""
	folder = path.expanduser(folder)
	if "*" in folder:
		files = glob.iglob(folder)
	elif path.isdir(folder):
		files = [path.join(folder, file) for file in os.listdir(folder)]
	else:
		return

	for file in files:
		if path.isfile(file) and "f" in mode or path.isdir(file) and "d" in mode:
			callback(file)
			
def expand(file):
	"""Expand user"""
	return path.expanduser(file)
	
def dirname(file):
	"""Get dirname"""
	return path.dirname(file)

@contextmanager	
def open(file, mode="r"):
	file = path.expanduser(file)
	prepare_folder(path.dirname(file))
	
	original = file
	if "w" in mode and is_file(file):
		file = file + time.strftime("@%Y-%m-%d_%H%M%S")
		encoding = "utf-8"
	else:
		encoding = "utf-8-sig"
		
	with io.open(file, mode, encoding=encoding) as fp:
		yield fp
	
	if file != original:
		os.replace(file, original)
		
def remove(file):
	file = path.expanduser(file)
	with suppress(FileNotFoundError):
		os.remove(file)

def json_load(file):
	"""My json.load"""
	with suppress(OSError):
		with open(file) as fp:
			return json.load(fp)
				
def json_dump(data, file):
	"""My json.dump"""
	
	def encoder(object):
		"""Encode any object to json."""
		if hasattr(object, "tojson"):
			return object.tojson()
		return vars(object)
		
	with open(file, "w") as fp:
		json.dump(
			data,
			fp,
			indent=4,
			ensure_ascii=False,
			default=encoder
		)
