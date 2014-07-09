#! python3

import subprocess
si = subprocess.STARTUPINFO()
si.dwFlags = subprocess.STARTF_USESHOWWINDOW
si.wShowWindow = subprocess.SW_HIDE

p = subprocess.Popen("py comiccrawlergui.py", startupinfo=si)
"""
data, er = p.communicate()
ret = p.wait()
if ret:
	import tkinter.messagebox as mb
	import tkinter as tk
	import traceback
	
	root = tk.Tk()
	root.withdraw()
	mb.showwarning("Comic Crawler", "發生錯誤!\n\n" + er.decode())
"""