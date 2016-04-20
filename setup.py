#! python3

import re

from setuptools import setup, find_packages
from os import path

here = path.abspath(path.dirname(__file__))

def read(file):
	with open(path.join(here, file), encoding='utf-8') as f:
		content = f.read()
	return content
	
def find_version(file):
	return re.search(r"__version__ = (\S*)", read(file)).group(1).strip("\"'")

setup(
	name = "comiccrawler",
	version = find_version("comiccrawler/__init__.py"),
	description = 'An image crawler with extendible modules and gui',
	long_description = read('README.rst'),
	url = 'https://github.com/eight04/ComicCrawler',
	author = 'eight',
	author_email = 'eight04@gmail.com',
	license = 'MIT',
	# See https://pypi.python.org/pypi?%3Aaction=list_classifiers
	classifiers = [
		'Development Status :: 5 - Production/Stable',
		"Environment :: Console",
		"Environment :: Win32 (MS Windows)",
		"Intended Audience :: End Users/Desktop",
		"License :: OSI Approved :: MIT License",
		"Natural Language :: Chinese (Traditional)",
		"Operating System :: Microsoft :: Windows :: Windows 7",
		"Programming Language :: Python :: 3.4",
		"Topic :: Internet"
	],
	keywords = 'image crawler',
	packages = ['comiccrawler'],
	install_requires = [
		"docopt~= 0.6.2", 
		"pyexecjs~= 1.3.1",
		"pythreadworker~= 0.3.0"
	],
	entry_points = {
		"console_scripts": [
			"comiccrawler = comiccrawler:console_init"
		]
	}
)
