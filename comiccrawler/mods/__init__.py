#! python3

"""comiccrawler.mods

Import all downloader modules
"""

from os.path import dirname, realpath, join, isdir, splitext, expanduser
from os import listdir
from importlib import import_module
from re import search
from sys import version_info

from ..config import config

def import_module_file(ns, file):
	if version_info < (3, 5):
		from importlib.machinery import SourceFileLoader
		module = SourceFileLoader(ns, file).load_module()
	else:
		from importlib.util import spec_from_file_location, module_from_spec
		spec = spec_from_file_location(ns, file)
		module = module_from_spec(spec)
		spec.loader.exec_module(module)
	return module
	
mods = set()
domain_index = {}
here = dirname(__file__)
	
"""Load mods"""	
for file in listdir(here):
	name, ext = splitext(file)
	if name == "__init__":
		continue
	if ext != ".py":
		continue
	mods.add(import_module("comiccrawler.mods." + name))
	
# Load mods from user mods dir
user_mods_dir = expanduser("~/comiccrawler/mods")
if isdir(user_mods_dir):
	for file in listdir(user_mods_dir):
		name, ext = splitext(file)
		if ext != ".py":
			continue
		mods.add(import_module_file("comiccrawler.user_mods." + name, join(user_mods_dir, file)))
	
"""Regist domain with mod to self.dlHolder"""
for mod in mods:
	for url in mod.domain:
		domain_index[url] = mod

def load_config():
	"""Load setting.ini and set up module.
	"""
	for mod in mods:
		if hasattr(mod, "config"):
			if mod.name not in config.config:
				config.config[mod.name] = {}
			for key, value in mod.config.items():
				if key not in config.config[mod.name]:
					config.config[mod.name][key] = value
			
		if mod.name not in config.config:
			mod.config = config.config["DEFAULT"]
		else:
			mod.config = config.config[mod.name]
			
		if hasattr(mod, "load_config"):
			mod.load_config()
			
load_config()

def list_domain():
	"""Return downloader dictionary."""
	return sorted(domain_index)
	
def get_module(url):
	"""Return the downloader mod of spect url or return None"""
	
	match = search("^https?://([^/]+?)(:\d+)?/", url)
	
	if not match:
		return None
		
	domain = match.group(1)
	
	while domain:
		if domain in domain_index:
			return domain_index[domain]
		try:
			domain = domain[domain.index(".") + 1:]
		except ValueError:
			break
	return None
