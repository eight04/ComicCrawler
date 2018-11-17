#!python3

"""This module provide a global setting object, which will save on exit.
"""

from configparser import ConfigParser
from os.path import expanduser, dirname, isdir, normpath
from os import makedirs

from .profile import get as profile

class CaseSensitiveConfigParser(ConfigParser):
	optionxform = str

class Config:
	default = {
		"savepath": "download",
		"runafterdownload": "",
		"libraryautocheck": "true",
		"autosave": "5",
		"errorlog": "false",
		"lastcheckupdate": "0",
		"selectall": "true",
		"mission_conflict_action": "update"
	}
	def __init__(self, path):
		self.path = expanduser(path)
		self.config = CaseSensitiveConfigParser(interpolation=None)
		self.load()
		
	def load(self):
		# this method doesn't raise error
		self.config.read(self.path, 'utf-8-sig')
		
		if "DEFAULT" not in self.config:
			self.config["DEFAULT"] = {}
		
		# backward compatible
		if "ComicCrawler" in self.config:
			self.config["DEFAULT"].update(self.config["ComicCrawler"])
			del self.config["ComicCrawler"]
		
		self.default.update(self.config['DEFAULT'])
		self.config['DEFAULT'].update(self.default)
		
		self.config['DEFAULT']["savepath"] = normpath(self.config['DEFAULT']["savepath"])
		
	def save(self):
		if not isdir(dirname(self.path)):
			makedirs(dirname(self.path))
		with open(self.path, 'w', encoding='utf-8') as f:
			self.config.write(f)
	
config = Config(profile('setting.ini'))
setting = config.config['DEFAULT']
