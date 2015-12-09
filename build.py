#! python3

import os.path as path, re, sys

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
		self.build()
		self.dist()
		self.git()
		self.install()

	def dist(self):
		import shutil, subprocess, sys

		subprocess.call([sys.executable, "setup.py", "sdist", "bdist_wheel"])
		subprocess.call(["twine", "upload", "dist/*"])
		shutil.rmtree("dist")

	def git(self):
		import subprocess
		from setup import settings
		version = settings["version"]
		subprocess.call(["git", "add", "-A", "."])
		subprocess.call(["git", "commit", "-m", "Release v" + version])
		subprocess.call(["git", "tag", "-a", "v" + version, "-m", "Release v" + version])
		subprocess.call(["git", "push", "--follow-tags"])

	def build(self):
		import re, comiccrawler.mods

		# Build readme
		readme = read("README-src.rst")

		version = find_version("comiccrawler/__init__.py")
		domains = " ".join(comiccrawler.mods.list_domains())

		readme = readme.replace("@@VERSION", version)
		readme = readme.replace("@@DOMAINS", domains)

		write("README.rst", readme)

		# Build setup.py
		setup = read("setup-src.py")

		setup = setup.replace("@@VERSION", repr(version))
		setup = setup.replace("@@README", repr(readme))

		write("setup.py", setup)

	def install(self):
		import subprocess
		subprocess.call(["pip", "install", "-e", "."])

if __name__ == "__main__":
	Tasker(Tasks)
