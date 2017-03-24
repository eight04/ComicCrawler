#! python3

import pathlib
import datetime
import re

from xcute import cute, split_version, conf, Exc

def bump():
	"""My bump task"""
	path = pathlib.Path('comiccrawler/__pkginfo__.py')
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
	pkg_name = "comiccrawler",
	default = "python -m comiccrawler gui",
	test = ['pylint comiccrawler', 'readme_build'],
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
		'twine upload dist/*{version}[.-]*',
		'git push --follow-tags'
	],
	publish_err = 'start https://pypi.python.org/pypi/comiccrawler/',
	install = 'pip install -e .',
	install_err = 'elevate -c -w pip install -e .',
	readme_build = [
		'python setup.py --long-description > build/long-description.rst',
		'rst2html --no-raw --exit-status=1 --verbose '
			'build/long-description.rst build/long-description.html'
	],
	readme_build_err = ['readme_show', Exc()],
	readme_show = 'start build/long-description.html',
	readme = 'readme_build',
	readme_post = 'readme_show'
)
