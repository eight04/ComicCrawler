#! python3

from os import getcwd
from os.path import expanduser, normpath, join

PROFILE = "~/comiccrawler"

def set(profile):
	global PROFILE
	PROFILE = profile

def get(file=None):
	if file is not None:
		return normpath(join(getcwd(), expanduser(PROFILE), expanduser(file)))
	return normpath(join(getcwd(), expanduser(PROFILE)))
