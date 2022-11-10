#! python3

"""comiccrawler.mods

Import all downloader modules
"""

from os.path import dirname, join, isdir, splitext
from os import listdir
from importlib import import_module
from re import search
from sys import version_info

from ..config import config
from ..profile import get as profile
from ..grabber import cooldown, get_session
from ..util import extract_curl
from ..url import urlparse

def setup_curl(d):
	for key, value in d.items():
		if key.startswith("curl") and value:
			url, headers, cookies = extract_curl(value)
			netloc = urlparse(url).netloc
			s = get_session(netloc)
			for key in list(headers.keys()):
				if key.startswith("If-"):
					headers.pop(key)
			s.headers.update(headers)
			s.cookies.update(cookies)

def import_module_file(ns, file):
	# pylint: disable=import-outside-toplevel
	if version_info < (3, 5):
		from importlib.machinery import SourceFileLoader
		# pylint: disable=deprecated-method, no-value-for-parameter
		module = SourceFileLoader(ns, file).load_module()
	else:
		from importlib.util import spec_from_file_location, module_from_spec
		spec = spec_from_file_location(ns, file)
		module = module_from_spec(spec)
		spec.loader.exec_module(module)
	return module
	
class ModLoader:
	def __init__(self):
		self.mods = set()
		self.domain_index = {}
		self.loaded = False
		
	def load(self):
		"""Load mods"""	
		if self.loaded:
			return
			
		# load from here
		for file in listdir(dirname(__file__)):
			name, ext = splitext(file)
			if name == "__init__":
				continue
			if ext != ".py":
				continue
			self.mods.add(import_module("comiccrawler.mods." + name))
			
		# load from user mods dir
		user_mods_dir = profile("mods")
		if isdir(user_mods_dir):
			for file in listdir(user_mods_dir):
				name, ext = splitext(file)
				if ext != ".py":
					continue
				self.mods.add(import_module_file(
					"comiccrawler.user_mods." + name, join(user_mods_dir, file)))
		
		# build index, update grabber cooldown
		for mod in self.mods:
			for url in mod.domain:
				self.domain_index[url] = mod
			cooldown.update(getattr(mod, "grabber_cooldown", {}))

		# init config
		for mod in self.mods:
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
				
		self.load_config()
		self.loaded = True
		
	def list_domain(self, include_mod = False):
		"""Return downloader dictionary."""
		self.load()
		if include_mod:
			return sorted(self.domain_index.items(), key=lambda i: i[0])
		return sorted(self.domain_index)
		
	def get_module(self, url):
		"""Return the downloader mod of spect url or return None"""
		self.load()
		
		match = search(r"^https?://([^/]+?)(:\d+)?/", url)
		
		if not match:
			return None
			
		domain = match.group(1)
		
		while domain:
			if domain in self.domain_index:
				return self.domain_index[domain]
			try:
				domain = domain[domain.index(".") + 1:]
			except ValueError:
				break
		return None
		
	def load_config(self):
		"""Reload config for mods"""
		for mod in self.mods:
			if mod.name in config.config and config.config[mod.name] != mod.config:
				mod.config = config.config[mod.name]
				
			if hasattr(mod, "load_config"):
				mod.load_config()

			if getattr(mod, "autocurl", False):
				setup_curl(mod.config)
	
mod_loader = ModLoader()
list_domain = mod_loader.list_domain
get_module = mod_loader.get_module
load_config = mod_loader.load_config
