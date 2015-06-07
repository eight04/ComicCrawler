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

import re

here = path.abspath(path.dirname(__file__))

def read(file):
	with open(path.join(here, file), encoding='utf-8') as f:
		content = f.read().replace("\r\n", "\n")
	return content
	
def find_version(file):
	return re.search(r"__version__ = (\S*)", read(file)).group(1).strip("\"'")
	
settings = {
	"name": "pythreadworker",
	"version": find_version("worker/__init__.py"),
	"description": 'A threading library written in python',
	# Get the long description from the relevant file
	"long_description": read("README.md"),
	"url": 'https://github.com/eight04/pyWorker',
	"author": 'eight',
	"author_email": 'eight04@gmail.com',
	"license": 'MIT',
	# See https://pypi.python.org/pypi?%3Aaction=list_classifiers
	"classifiers": [
		'Development Status :: 5 - Production/Stable',

		# Indicate who your project is intended for
		'Intended Audience :: Developers',
		'Topic :: Software Development :: Libraries :: Python Modules',

		# Pick your license as you wish (should match "license" above)
		'License :: OSI Approved :: MIT License',

		# Specify the Python versions you support here. In particular, ensure
		# that you indicate whether you support Python 2, Python 3 or both.
		'Programming Language :: Python :: 3.4'
	],
	"keywords": 'thread',
	"packages": find_packages(),
}

if __name__ == "__main__":	
	setup(**settings)
