DOIT_CONFIG = {
	"default_tasks": ["build", "test"],
	"verbosity": 2
}

# Make it always run in root
import os
os.chdir(os.path.abspath(os.path.dirname(__file__)))

class Replacer:
	def __init__(self, dict):
		import re
		self.patterns = []
		for pattern, replace in dict.items():
			pattern = re.compile(pattern)
			self.patterns.append((pattern, replace))
		
	def do(self, *files):
		import pathlib
		for file in files:
			file = pathlib.Path(file)
			content = file.read_text(encoding="utf-8")
			for pattern, replace in self.patterns:
				content = pattern.sub(replace, content)
			file.write_text(content, encoding="utf-8")
		
	def replacer(self, match):
		return self.dict[match.group()]
		
def task_build():

	def build(targets):
		import comiccrawler.mods
		
		domains = " ".join(comiccrawler.mods.list_domain())
		
		Replacer({
			r"\.\. DOMAINS[\s\S]+?\.\. END DOMAINS": ".. DOMAINS\n..\n\n    " + domains + "\n\n.. END DOMAINS"
		}).do("README.rst")
		
	return {
		"actions": [build]
	}
	
def task_git():
	from comiccrawler import __version__ as v
	
	return {
		"actions": [
			"git add -A .",
			"git commit -m \"Release v{}\"".format(v),
			"git tag -a v{0} -m \"Release v{0}\"".format(v),
			"git push --follow-tags"
		]
	}
	
def task_install():
	return {
		"actions": ["pip install -e ."]
	}
	
def task_test():
	return {
		"actions": ["py setup.py check -r"]
	}
	
def task_upload():
	from comiccrawler import __version__ as v
	
	return {
		"actions": ["twine upload dist/*{}*".format(v)]
	}
	
def task_dist():
	return {
		"actions": ["py setup.py sdist bdist_wheel"]
	}

def task_bump():
	def bump():
		import datetime, comiccrawler
		pre_version = comiccrawler.__version__
		today = datetime.date.today()
		version = "{}.{}.{}".format(today.year, today.month, today.day)
		if pre_version.startswith(version):
			if version == pre_version:
				version += ".1"
			else:
				version += ".{}".format(int(pre_version.split(".")[3]) + 1)
				
		# write to files
		Replacer({pre_version: version}).do("setup.py", "comiccrawler/__init__.py")
		
	return {
		"actions": [
			"doit build test",
			bump,
			"doit dist upload git install"
		]
	}
