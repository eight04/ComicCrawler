#! python3

import argparse,os

parser = argparse.ArgumentParser(description='helper for ComicCrawler in windows')
parser.add_argument('-p',help='set a python path if not using default one')
parser.add_argument('-d',action='store_true',help='install dependencies')

args = parser.parse_args()

if args.d:
	pipStr = 'pip'
	if args.p:
		pipStr = args.p + '/Scripts/' + pipStr
	dependencies = [
	'docopt',
	'pyexecjs',
	'pythreadworker',
	'safeprint',
	'requests',
	'wheel',
	'twine',
	'docutils',
	'pyxcute'
	]
	for d in dependencies:
		os.system(pipStr + ' install ' + d + ' --upgrade')
else:
	pythonStr = 'python'
	ccStr = 'comiccrawler'
	if args.p:
		pythonStr = args.p + '/' + pythonStr
		ccStr = args.p + '/Scripts/' + ccStr	
	os.system(pythonStr + ' setup.py build')
	os.system(pythonStr + ' setup.py install')
	os.system(ccStr + ' gui')
