from .config import setting
from .io import content_write
from .profile import get as profile

def debug_log(*args):
	if setting.getboolean("errorlog"):
		content_write(profile("debug.log"), ", ".join(args) + "\n", append=True)
