#! python3

import pathlib
import datetime

from xcute import cute, Version, split_version, conf

def bump():
	"""My bump task"""
	path = pathlib.Path('comiccrawler/__init__.py')
	text = path.read_text(encoding='utf-8')
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
	path.write_text(left + version + right)

cute(
	test = 'setup check -r',
	bump_pre = 'test',
	bump = bump,
	bump_post = ['dist', 'release', 'publish', 'install'],
	dist = 'python setup.py sdist bdist_wheel',
	release = [
		'git add .',
		'git commit -m "Release v{version}"',
		'git tag -a v{version} -m "Release v{version}"'
	],
	publish = [
		'twine upload dist/*{version}*',
		'git push --follow-tags'
	],
	install = 'pip install -e .',
	install_err = 'elevate -c -w pip install -e .',
	readme = 'python setup.py --long-description > %temp%/ld && rst2html --no-raw %temp%/ld %temp%/ld.html && start %temp%/ld.html',
	version = [Version('comiccrawler/__init__.py'), 'echo {version}']
)
