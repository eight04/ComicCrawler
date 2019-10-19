#! python3

import re
import subprocess # nosec
import traceback
import platform

# Translate state code to readible text.
STATE = {
	"INIT": "準備",
	"ANALYZED": "解析完成",
	"DOWNLOADING": "下載中",
	"PAUSE": "停止",
	"FINISHED": "完成",
	"ERROR": "錯誤",
	"INTERRUPT": "已刪除",
	"UPDATE": "有更新",
	"ANALYZING": "分析中",
	"ANALYZE_INIT": "準備分析"
}

def safe_tk(text):
	"""Encode U+FFFF+ characters. Tkinter doesn't allow to display these
	character. See:
	http://stackoverflow.com/questions/23530080/how-to-print-non-bmp-unicode-characters-in-tkinter-e-g
	"""

	return re.sub(r"[^\u0000-\uFFFF]", "_", text)
	
def get_scale(root):
	"""To display in high-dpi we need to grab the scale factor from OS"""
	
	# There is no solution on XP
	if platform.system() == "Windows" and platform.release() == "XP":
		return 1.0
	
	# Windows
	# https://github.com/eight04/ComicCrawler/issues/13#issuecomment-229367171
	try:
		# pylint: disable=import-outside-toplevel
		from ctypes import windll
		user32 = windll.user32
		user32.SetProcessDPIAware()
		w = user32.GetSystemMetrics(0)
		return w / root.winfo_screenwidth()
	except ImportError:
		# non-windows
		pass
	except Exception: # pylint: disable=broad-except
		traceback.print_exc()
	
	# GNome
	args = ["gsettings", "get", "org.gnome.desktop.interface", "scaling-factor"]
	try:
		with subprocess.Popen(args, stdout=subprocess.PIPE, # nosec
				universal_newlines=True) as p:
			return float(p.stdout.read().rpartition(" ")[-1])
	except Exception: # pylint: disable=broad-except
		traceback.print_exc()
		
	return 1.0
