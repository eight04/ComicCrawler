DOIT_CONFIG = {
	"default_tasks": ["build", "test", "dist", "upload", "git", "install"],
	"verbosity": 2
}

# Make it always run in root
import os
os.chdir(os.path.abspath(os.path.dirname(__file__)))

def read(file):
	with open(file, "r", encoding='utf-8') as f:
		content = f.read()
	return content

def write(file, content):
	with open(file, "w", encoding="utf-8") as f:
		f.write(content)
		
class Replacer:
	def __init__(self, dict):
		import re
		self.dict = dict
		self.pattern = re.compile("|".join(dict.keys()))
		
	def do(self, text):
		return self.pattern.sub(self.replacer, text)
		
	def replacer(self, match):
		return self.dict[match.group()]
		

def task_build():

	def build(targets):
		import comiccrawler, comiccrawler.mods
		
		replacer = Replacer({
			"@@VERSION": comiccrawler.__version__,
			"@@DOMAINS": " ".join(comiccrawler.mods.list_domain())
		})
		
		for target in targets:
			write(target.replace("-src", ""), replacer.do(read(target)))
		
	return {
		"actions": [build],
		"targets": ["README-src.rst", "setup-src.py"]
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
		"actions": ["twine upload %(targets)s"],
		"targets": ["dist/*" + v + "*"]
	}
	
def task_dist():
	return {
		"actions": ["py setup.py sdist bdist_wheel"]
	}
