#! python3

"""comiccrawler.mods

Import all downloader modules
"""

from os.path import dirname, realpath, join
from os import listdir
from importlib import import_module
from re import search

from ..config import section, setting
	
mods = set()
domain_index = {}
here = dirname(__file__)
	
"""Load mods"""	
for file in listdir(here):
	if file == "__init__.py":
		continue
	if not file.endswith(".py"):
		continue
	mod = file.replace(".py", "")
	mods.add(import_module("comiccrawler.mods." + mod))
	
"""Regist domain with mod to self.dlHolder"""
for mod in mods:
	for url in mod.domain:
		domain_index[url] = mod

def load_config():
	"""Load setting.ini and set up module.
	"""
	for mod in mods:
		if hasattr(mod, "config"):
			mod.config = section(mod.name, mod.config)
		if hasattr(mod, "loadconfig"):
			mod.loadconfig()
			
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
