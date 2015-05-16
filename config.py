#!python3

"""
This module provide a global setting object, which will save on exit.

Usage:
  # Basic
  import config
  config.load("some-file")
  config.setting["key"] = "value"
  config.save()
  
  # Use other section
  sec1 = config.section("label1")
  sec1["key"] = "value"
  
  # Set default value
  default = {
    "key1": "value1",
	"key2": "value2"
  }
  sec2 = config.section("label2", default)
  print(sec2["key1"])
  # -> "value1"
"""

import configparser, atexit

def section(name, default = None):
	if name not in config:
		config[name] = {}

	if default:
		for key in default:
			if key not in config[name]:
				config[name][key] = default[key]
				
	return config[name]
	
def get(key, default = None):
	if key not in setting:
		setting[key] = default
	return setting[key]
	
def setPath(func):
	def _setPath(newPath = None):
		if newPath is not None:
			global path
			path = newPath
		func()
	return _setPath

@setPath
def load():
	config.read(path, "utf-8-sig")
	
@setPath
def save():
	with open(path, "w", encoding="utf-8") as file:
		config.write(file)

path = "setting.ini"
config = configparser.ConfigParser(interpolation=None)
load()
setting = section("DEFAULT")
atexit.register(save)
