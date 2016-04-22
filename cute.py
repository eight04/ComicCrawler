#! python3

import pathlib
import datetime
import re

from xcute import cute, Version, split_version, conf

def bump():
	"""My bump task"""
	path = pathlib.Path('comiccrawler/__init__.py')
	text = path.read_text('utf-8')
	left, old_version, right = split_version(text)
	old_version = tuple(int(token) for token in old_version.split("."))
	date = datetime.datetime.now()
	version = (date.year, date.month, date.day)
	if version < old_version:
		version += (old_version[3] + 1,)
	elif version == old_version:
		version += (1,)
	version = ".".join(map(str, version))
	conf["version"] = version
	path.write_text(left + version + right, 'utf-8')
	
def split_domains(text):
	"""Split text into left, domains, right"""
	match = re.search(r'\.\. DOMAINS\s*\.\.\s*([\s\S]+?)\s*\.\. END DOMAINS', text)
	i = match.start(1)
	j = match.end(1)
	return text[:i], text[i:j], text[j:]
	
def domains():
	"""Update domains"""
	from comiccrawler.mods import list_domain
	domains = " ".join(list_domain())
	path = pathlib.Path('README.rst')
	text = path.read_text('utf-8')
	left, old_domains, right = split_domains(text)
	if old_domains == domains:
		return
	path.write_text(left + domains + right, 'utf-8')

cute(
	test = 'setup check -r',
	bump_pre = 'test',
	bump = bump,
	bump_post = ['domains', 'dist', 'release', 'publish', 'install'],
	domains = domains,
	dist = 'python setup.py sdist bdist_wheel',
	release = [
		'git add .',
		'git commit -m "Release v{version}"',
		'git tag -a v{version} -m "Release v{version}"'
	],
	publish = [
		'twine upload dist/comiccrawler-{version}.zip dist/comiccrawler-{version}-py3-none-any.whl',
		'git push --follow-tags'
	],
	install = 'pip install -e .',
	install_err = 'elevate -c -w pip install -e .',
	readme = 'python setup.py --long-description > %temp%/ld && rst2html --no-raw %temp%/ld %temp%/ld.html && start %temp%/ld.html',
	version = [Version('comiccrawler/__init__.py'), 'echo {version}']
)
