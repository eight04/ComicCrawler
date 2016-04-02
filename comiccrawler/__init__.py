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
  migrate             Migrate from old version, convert save file to new
                      format.

Options:
  --dest SAVE_FOLDER  Set download save path. [default: .]
  --help              Show help message.
  --version           Show current version.

Sub modules:
  comiccrawler.core   Core functions of downloading, analyzing.
  comiccrawler.error  Errors.
  comiccrawler.mods   Import download modules.
"""

__version__ = "2016.4.2"

def console_download(url, savepath):
	"""Download url to savepath."""
	from worker import Worker
	from .core import Mission, download, analyze

	mission = Mission(url=url)
	Worker.sync(analyze, mission, pass_instance=True)
	Worker.sync(download, mission, savepath, pass_instance=True)

def console_init():
	"""Console init."""
	from docopt import docopt

	arguments = docopt(__doc__, version="Comic Crawler v" + __version__)

	if arguments["domains"]:
		from .mods import list_domain
		print("Supported domains:\n" + ", ".join(list_domain()))

	elif arguments["gui"]:
		from .gui import MainWindow
		MainWindow().run()

	elif arguments["download"]:
		console_download(arguments["URL"], arguments["savepath"])

	elif arguments["migrate"]:
		from .migrate import migrate
		migrate()
