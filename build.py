#! python3

import os, os.path as path, re

here = path.abspath(path.dirname(__file__))

def read(file):
	with open(path.join(here, file), "r", encoding='utf-8') as f:
		content = f.read().replace("\r\n", "\n")
	return content
	
def write(file, content):
	with open(path.join(here, file), "w", encoding="utf-8") as f:
		f.write(content)
	
def find_version(file):
	return re.search(r"__version__ = (\S*)", read(file)).group(1).strip("\"'")	

if __name__ == "__main__":
	from comiccrawler.mods import list_domain
	write(
		"README.md",
		read("README.src.md").replace(
			"@@SUPPORTED_DOMAINS",
			" ".join(list_domain())
		)
	)
	
	from setup import settings
	import os
	version = settings["version"]
	os.system("py setup.py sdist bdist_wheel")
	os.system("twine upload dist/*")
	os.system("rm -R dist")
	os.system("git add -A .")
	os.system('git commit -m "Release v{}"'.format(version))
	os.system('git tag -a v{} -m "Release v{}"'.format(version, version))
	os.system("git push --follow-tags")
