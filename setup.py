#! python3

"""A setuptools based setup module.

See:
https://packaging.python.org/en/latest/distributing.html
https://github.com/pypa/sampleproject
"""

# Always prefer setuptools over distutils
from setuptools import setup, find_packages
# To use a consistent encoding
from codecs import open
from os import path

import re, pypandoc

here = path.abspath(path.dirname(__file__))

def read(file):
	with open(path.join(here, file), encoding='utf-8') as f:
		content = f.read().replace("\r\n", "\n")
	return content
	
def find_version(file):
	return re.search(r"__version__ = (\S*)", read(file)).group(1).strip("\"'")
	
settings = {
	"name": "comiccrawler",
	"version": find_version("comiccrawler/__init__.py"),
	"description": 'An image crawler with extendible modules and gui',
	# Get the long description from the relevant file
	"long_description": pypandoc.convert("README.md", "rst"),
	"url": 'https://github.com/eight04/ComicCrawler',
	"author": 'eight',
	"author_email": 'eight04@gmail.com',
	"license": 'MIT',
	# See https://pypi.python.org/pypi?%3Aaction=list_classifiers
	"classifiers": [
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
	"keywords": 'crawler',
	"packages": find_packages(),
	"install_requires": ["pyexecjs", "pythreadworker"]
	"entry_points": {
		"console_scripts": [
			"comiccrawler = comiccrawler:console_init"
		]
	}
}

if __name__ == "__main__":	
	setup(**settings)
