#! python3

import os, os.path as path, re, sys

here = path.abspath(path.dirname(__file__))

def read(file):
	with open(path.join(here, file), "r", encoding='utf-8') as f:
		content = f.read()
	return content

def write(file, content):
	with open(path.join(here, file), "w", encoding="utf-8") as f:
		f.write(content)

def find_version(file):
	return re.search(r"__version__ = (\S*)", read(file)).group(1).strip("\"'")

class Tasker:
	def __init__(self, task_cls):
		tasks = task_cls()
		argv = sys.argv[1:]

		if not argv:
			argv = ["default"]

		for command in argv:
			command, sep, param = command.partition(":")

			if sep:
				getattr(tasks, command)(param)
			else:
				getattr(tasks, command)()

class Tasks:
	def default(self):
		self.readme()
		self.dist()
		self.bump()
		self.install()

	def dist(self):
		import os
		os.system("py setup.py sdist bdist_wheel")
		os.system("twine upload dist/*")
		os.system("rm -R dist")

	def bump(self):
		import os
		from setup import settings
		version = settings["version"]
		os.system("git add -A .")
		os.system('git commit -m "Release v{}"'.format(version))
		os.system('git tag -a v{} -m "Release v{}"'.format(version, version))
		os.system("git push --follow-tags")

	def readme(self):
		from comiccrawler.mods import list_domain
		from setup import settings
		version = settings["version"]

		# Create readme
		write(
			"README.md",
			read("README.src.md").replace(
				"@@SUPPORTED_DOMAINS",
				" ".join(list_domain())
			).replace("@@VERSION", version)
		)

	def install(self):
		import os
		os.system("pip install -e .")

if __name__ == "__main__":
	Tasker(Tasks)
