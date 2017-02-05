#! python3

"""Comic Crawler

Usage:
  comiccrawler domains
  comiccrawler download URL [--dest SAVE_FOLDER]
  comiccrawler gui
  comiccrawler migrate
  comiccrawler (--help | --version)

Commands:
  domains             List supported domains.
  download URL        Download from the URL.
  gui                 Launch TKinter GUI.
  migrate             Convert old file path to new file path.

Options:
  --dest SAVE_FOLDER  Set download save path. [default: .]
  --help              Show help message.
  --version           Show current version.

Sub modules:
  comiccrawler.core   Core functions of downloading, analyzing.
  comiccrawler.error  Errors.
  comiccrawler.mods   Import download modules.
"""

__version__ = "2017.2.5"

def console_download(url, savepath):
	"""Download url to savepath."""
	from .core import Mission, download, analyze

	mission = Mission(url=url)
	analyze(mission)
	download(mission, savepath)

def console_init():
	"""Console init."""
	from docopt import docopt

	arguments = docopt(__doc__, version="Comic Crawler v" + __version__)

	if arguments["domains"]:
		from .mods import list_domain
		print("Supported domains:\n" + ", ".join(list_domain()))

	elif arguments["gui"]:
		from .gui import MainWindow
		MainWindow()

	elif arguments["download"]:
		console_download(arguments["URL"], arguments["--dest"])
		
	elif arguments["migrate"]:
		migrate()

def migrate():
	import re
	
	from .mission_manager import mission_manager, get_mission_id
	from .core import safefilepath
	from .io import move
	from .safeprint import print
	
	def safefilepath_old(s):
		"""Return a safe directory name."""
		return re.sub("[/\\\?\|<>:\"\*]","_",s).strip()
		
	def rename(l):
		for src, dst in l:
			if src != dst:
				print("\n" + src + "\n" + dst)
				move(src, dst)
		
	mission_manager.load()
	to_rename = []
	
	for mission in mission_manager.pool.values():
		id = get_mission_id(mission)
		old_ep = "~/comiccrawler/pool/" + safefilepath_old(id + ".json")
		new_ep = "~/comiccrawler/pool/" + safefilepath(id + ".json")
		to_rename.append((old_ep, new_ep))
		
	rename(to_rename)
	