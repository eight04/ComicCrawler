#! python3

"""Comic Crawler

Usage:
  comiccrawler domains
  comiccrawler download URL [--dest SAVE_FOLDER]
  comiccrawler gui
  comiccrawler (--help | --version)

Commands:
  domains             List supported domains.
  download URL        Download from the URL.
  gui                 Launch TKinter GUI.

Options:
  --dest SAVE_FOLDER  Set download save path. [default: .]
  --help              Show help message.
  --version           Show current version.

Sub modules:
  comiccrawler.core   Core functions of downloading, analyzing.
  comiccrawler.error  Errors.
  comiccrawler.mods   Import download modules.
"""

__version__ = "2016.7.1"

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
