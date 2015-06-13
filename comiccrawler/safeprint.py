#! python3

"""This is safeprint module.

"""
import os, re

def match_escape_echo(match):
	"""Return escaped echo str."""
	return "^" + match.group()

def printer_echo(s):
	"""Use system echo."""
	for line in s.split("\n"):
		line = re.sub(r"[\&<>|^]", match_escape_echo, line)
		os.system('echo:' + line)

def printer_try(s):
	"""Use try, catch in python."""
	for c in s:
		try:
			print(c, end="")
		except UnicodeEncodeError:
			print("?", end="")
	print("")

def safeprint(*ss):
	"""Safe print, skip error decode."""
	ss = [s if type(s) is str else str(s) or str(type(s)) for s in ss]
	s = " ".join(ss)

	printer_echo(s)

	for f in _callbacklist:
		f(s)

_callbacklist = []
def addcallback(callback):
	if callback in _callbacklist:
		return
	if callable(callback):
		_callbacklist.append(callback)

def removecallback(callback):
	if callback in _callbacklist:
		_callbacklist.remove(callback)

if __name__ == "__main__":
	safeprint("Hello World!", "你好世界！", "ハローワールド", "हैलो वर्ल्ड")
