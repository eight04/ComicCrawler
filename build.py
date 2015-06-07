#! python3

import os
from setup import settings

version = settings["version"]

os.system("py setup.py sdist bdist_wheel")
os.system("twine upload dist/*")
os.system("rm -R dist")
os.system("git add -A .")
os.system('git commit -m "Release v{}"'.format(version))
os.system('git tag -a v{} -m "Release v{}"'.format(version, version))
os.system("git push --follow-tags")
