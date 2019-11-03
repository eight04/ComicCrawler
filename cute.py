#! python3

from xcute import cute, Bump, LiveReload

def date_bumper(old_version):
	"""My bump task"""
	from datetime import datetime
	old_version = tuple(int(token) for token in old_version.split("."))
	date = datetime.now()
	version = (date.year, date.month, date.day)
	if version < old_version:
		version += (old_version[3] + 1,)
	elif version == old_version:
		version += (1,)
	return ".".join(map(str, version))
	
def split_domains(text):
	"""Split text into left, domains, right"""
	import re
	match = re.search(r'\.\. DOMAINS\s*\.\.\s*([\s\S]+?)\s*\.\. END DOMAINS', text)
	i = match.start(1)
	j = match.end(1)
	return text[:i], text[i:j], text[j:]
	
def domains():
	"""Update domains"""
	import pathlib
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
	bump = Bump("{version_file}", date_bumper),
	bump_post = ['domains', 'dist', 'release', 'publish', 'install'],
	domains = domains,
	dist = 'x-clean build dist *.egg-info && python setup.py sdist bdist_wheel',
	release = [
		'git add .',
		'git commit -m "Release v{version}"',
		'git tag -a v{version} -m "Release v{version}"'
	],
	publish = [
		'twine upload dist/*',
		'git push --follow-tags'
	],
	install = 'pip install -e .',
	install_err = 'elevate -c -w pip install -e .',
	readme_build = [
		'python setup.py --long-description | x-pipe build/readme/index.rst',
		'rst2html5.py --no-raw --exit-status=1 --verbose '
			'build/readme/index.rst build/readme/index.html'
	],
	readme_pre = "readme_build",
	readme = LiveReload("README.rst", "readme_build", "build/readme")
)
