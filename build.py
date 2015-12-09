#! python3

import os, os.path as path, re, sys

# Make it always run in root
os.chdir(path.abspath(path.dirname(__file__)))

def read(file):
	with open(file, "r", encoding='utf-8') as f:
		content = f.read()
	return content

def write(file, content):
	with open(file, "w", encoding="utf-8") as f:
		f.write(content)

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
		self.upload()
		self.git()
		self.install()

	def dist(self):
		import subprocess, sys
		subprocess.call([sys.executable, "setup.py", "sdist", "bdist_wheel"])

	def upload(self):
		import subprocess, comiccrawler
		subprocess.call(["twine", "upload", "dist/*" + comiccrawler.__version__ +  "*"])

	def git(self):
		import subprocess, comiccrawler

		version = comiccrawler.__version__

		subprocess.call(["git", "add", "-A", "."])
		subprocess.call(["git", "commit", "-m", "Release v" + version])
		subprocess.call(["git", "tag", "-a", "v" + version, "-m", "Release v" + version])
		subprocess.call(["git", "push", "--follow-tags"])

	def build(self):
		import re, comiccrawler, comiccrawler.mods

		# Build readme
		readme = read("README-src.rst")

		version = comiccrawler.__version__
		domains = " ".join(comiccrawler.mods.list_domain())

		readme = readme.replace("@@VERSION", version)
		readme = readme.replace("@@DOMAINS", domains)

		write("README.rst", readme)

		# Build setup.py
		setup = read("setup-src.py")

		setup = setup.replace("@@VERSION", repr(version))

		write("setup.py", setup)

	def install(self):
		import subprocess
		subprocess.call(["pip", "install", "-e", "."])

if __name__ == "__main__":
	Tasker(Tasks)
