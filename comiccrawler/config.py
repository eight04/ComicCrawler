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
  sec2 = config.section("label2", default=default)
  print(sec2["key1"])
"""

import configparser, atexit

from .io import prepare_file

def section(name, default = None):
	"""Return the section of the config."""
	if name not in config:
		config[name] = {}

	if default:
		for key in default:
			if key not in config[name]:
				config[name][key] = default[key]
				
	return config[name]
	
def load(new_path=None):
	"""Load config from file."""
	global path
	if new_path:
		path = new_path
	path = prepare_file(path)
	config.read(path, "utf-8-sig")
	
def save(new_path=None):
	"""Save config to file."""
	global path
	if new_path:
		path = new_path
	path = prepare_file(path)
	with open(path, "w", encoding="utf-8") as file:
		config.write(file)

path = "~/comiccrawler/setting.ini"
config = configparser.ConfigParser(interpolation=None)
load()
setting = section("DEFAULT")
atexit.register(save)
