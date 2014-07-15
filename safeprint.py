#! python3

"""This is safeprint module.

"""

def safeprint(*ss):
	"""Safe print, skip error decode."""
	
	ss = [s if type(s) is str else str(s) or str(type(s)) for s in ss]
	s = " ".join(ss)

	for c in s:
		try:
			print(c,end="")
		except Exception:
			print("?",end="")
				
	print("")
	
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
	
