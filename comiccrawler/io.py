#! python3

"""Simple io module depress exceptions"""

import os, os.path as path, pprint

def is_file(file):
	file = path.expanduser(file)
	
	return path.isfile(file)

def content_write(file, content):
	file = path.expanduser(file)
	
	if not path.isdir(path.dirname(file)):
		os.makedirs(path.dirname(file))
	
	if isinstance(content, bytes):
		with open(file, "wb") as f:
			f.write(content)
			
	else:				
		if not isinstance(content, str):
			content = pprint.pformat(content)
			
		with open(file, "w", encoding="utf-8") as f:
			f.write(content)	
		
def content_read(file):
	file = path.expanduser(file)
	
	if not path.isfile(file):
		return ""
	
	with open(file, "r", encoding="utf-8-sig") as f:
		return f.read()

def prepare_file(file):
	file = path.expanduser(file)
	
	if not path.isdir(path.dirname(file)):
		os.makedirs(path.dirname(file))
		
	if not path.isfile(file):
		open(file, "w").close()
	
	return file
