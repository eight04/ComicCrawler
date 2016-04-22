#!python3

"""This module provide a global setting object, which will save on exit.
"""

from configparser import ConfigParser
from os.path import expanduser, dirname, isdir, normpath
from os import makedirs

class Config:
	default = {
		"savepath": "~/comiccrawler/download",
		"runafterdownload": "",
		"libraryautocheck": "true",
		"autosave": "5",
		"errorlog": "false",
		"lastcheckupdate": "0"
	}
	def __init__(self, path):
		self.path = expanduser(path)
		self.config = ConfigParser(interpolation=None)
		self.load()
		
	def load(self):
		# this method doesn't raise error
		self.config.read(self.path, 'utf-8-sig')
		
		# Replace DEFAULT section with ComicCrawler section to avoid leaking personal data
		if 'ComicCrawler' not in self.config:
			self.config['ComicCrawler'] = {}
		
		if 'DEFAULT' in self.config:
			for key in self.default:
				if key in self.config['DEFAULT']:
					self.config['ComicCrawler'][key] = self.config['DEFAULT'][key]
					del self.config['DEFAULT'][key]
			# if not self.config['DEFAULT']:
				# del self.config['DEFAULT']
		
		# if 'DEFAULT' not in self.config:
			# self.config['DEFAULT'] = {}
		self.default.update(self.config['ComicCrawler'])
		self.config['ComicCrawler'].update(self.default)
		
		self.config['ComicCrawler']["savepath"] = normpath(self.config['ComicCrawler']["savepath"])
		
	def save(self):
		if not isdir(dirname(self.path)):
			makedirs(dirname(self.path))
		with open(self.path, 'w', encoding='utf-8') as f:
			self.config.write(f)
	
config = Config('~/comiccrawler/setting.ini')
setting = config.config['ComicCrawler']
