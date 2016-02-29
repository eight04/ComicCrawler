#! python3

"""A setuptools based setup module.

See:
https://packaging.python.org/en/latest/distributing.html
https://github.com/pypa/sampleproject
"""

# Always prefer setuptools over distutils
from setuptools import setup, find_packages
from os import path

here = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open(path.join(here, 'README.rst'), encoding='utf-8') as f:
    long_description = f.read()

settings = {
	"name": "comiccrawler",
	"version": '2016.2.29',
	"description": 'An image crawler with extendible modules and gui',
	# Get the long description from the relevant file
	"long_description": long_description,
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
	"install_requires": ["docopt", "pyexecjs", "pythreadworker"],
	"entry_points": {
		"console_scripts": [
			"comiccrawler = comiccrawler:console_init"
		]
	}
}

if __name__ == "__main__":
	setup(**settings)
