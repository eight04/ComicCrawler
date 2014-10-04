#! python3

"""Worker

A threaded worker, implemented with message queue and parent/child pattern."""

import queue, threading

class F:
	"""A data class. Define the message flags"""
	
	BUBBLE = 1
	BROADCAST = 2

class StopWorker(Exception): pass

class Worker:
	"""Wrap Thread class. Inherit MessageTree for thread communication."""
	
	def __init__(self, target=None):
		"""init"""
		
		self.error = queue.Queue()
		if callable(target):
			self.worker = target
		self.threading = None
		self.running = False
		self.messageBucket = queue.Queue()
		# self.messageCached = []
		self.children = set()
		self.parent = None
		self.args = []
		self.kwargs = {}
		self.ret = None
		
	def bubble(self, message, param=None):
		"""Shorthand to bubble message"""
		
		self.sendMessage(self.parent, message, param, F.BUBBLE)
		
	def broadcast(self, message, param=None):
		"""Shorthand to broadcast message"""
		
		for child in self.children:
			self.sendMessage(child, message, param, F.BROADCAST)
	
	def sendMessage(self, getter, message, param=None, flag=0):
		"""Send message to other threads"""
		
		if not issubclass(type(getter), Worker):
			raise TypeError("Not inherit Worker.")
		getter.message(message, param, flag, self)
		return self
		
	def message(self, message, param=None, flag=0, sender=None):
		"""Override"""
		
		if self.running:
			self.messageBucket.put((message, param, flag, sender))
		else:
			self.transferMessage(message, param, flag, sender)

		return self
			
	def transferMessage(self, message, param, flag, sender):
		"""Bubble and broadcast"""
		
		if F.BUBBLE & flag and self.parent and self.parent != sender:
			self.sendMessage(self.parent, message, param, flag)
			
		if F.BROADCAST & flag:
			for child in self.children:
				if child != sender:
					self.sendMessage(child, message, param, flag)
					
		return self
					
	def _onMessage(self, message, param, flag, sender):
		"""Message holder container, to ensure to transfer message"""
		
		self.transferMessage(message, param, flag, sender)
		ret = self.onMessage(message, param, sender)
		return ret
	
	def onMessage(self, message, param, sender):
		"""Override"""
		
		if message == "STOP_THREAD":
			raise StopWorker

		if message == "CHILD_THREAD_END":
			return self.removeChild(sender)
			
		if message == "CHILD_THREAD_ERROR":
			pass
			
		if message == "PAUSE_THREAD":
			return self.wait("RESUME_THREAD")
			
		return param
		
	def wait(self, arg, sender=None):
		"""Wait for specify message or wait specify duration.
		
		`arg` could be int or str. If `arg` is int, this function will wait 
		`arg` seconds. 
		
		If arg is str, this function will take the second param `sender`.
		If sender is provided, this function will wait till getting specify
		message `arg` which was sent by `sender`. If sender is None, this 
		function just returned after getting specify message.
		"""
		if type(arg) in [int, float]:
			import time
			
			while True:
				timeIn = time.time()
				try:
					message = self.messageBucket.get(timeout=arg)
				except queue.Empty:
					return
				else:
					# ret = self._onMessage(*message)
					# self.messageCached.append((message, ret))
					self._onMessage(*message)
					arg -= time.time() - timeIn
					if arg <= 0:
						return
				
		elif type(arg) is str:
			# cached = None
			# for cache in self.messageCached:
				# if cache[0][0] == arg and (not sender or sender == cache[0][3]):
					# cached = cache
			# if cached:
				# self.messageCached.remove(cached)
				# return cached[1]	# cached result
				
			while True:
				message = self.messageBucket.get()
				ret = self._onMessage(*message)
				if message[0] == arg and (not sender or sender == message[3]):
					return ret
				# self.messageCached.append((message, ret))
		
	def _worker(self):
		"""Real target to pass to threading.Thread"""

		try:
			self.ret = self.worker(*self.args, **self.kwargs)
		except StopWorker:
			pass
		except Exception as er:
			if self.threading:
				self.error.put(er)
			else:
				raise er
			if self.parent:
				self.sendMessage(self.parent, "CHILD_THREAD_ERROR", er)

		try:
			self.cleanup()
		except Exception as er:
			self.error.put(er)
		
		self.stopAllChild()
		while len(self.children):
			self.wait("CHILD_THREAD_END")
		
		self.running = False
		if self.parent:
			self.sendMessage(self.parent, "CHILD_THREAD_END", self.ret)
		
	def worker(self, *args, **kwargs):
		"""Override"""
		pass
		
	def cleanup(self, *args, **kwargs):
		"""Override"""
		pass
		
	def run(self, *args, **kwargs):
		"""Run as main thread"""
		self.args = args
		self.kwargs = kwargs
		self.running = True
		self._worker()
		return self.ret
		
	def stopAllChild(self):
		"""Stop all child threads"""
		
		child = None
		for child in self.children:
			self.stop(child)
		return child

	def start(self, *args, **kwargs):
		"""call this method and self.worker will run in new thread"""

		if self.running:
			return False
			
		self.running = True
		self.args = args
		self.kwargs = kwargs
		self.threading = threading.Thread(target=self._worker)
		self.threading.start()
		return self
		
	def stop(self, child=None):
		"""Stop self or child thread"""
		
		if not self.running:
			return False
			
		if not child:
			self.message("STOP_THREAD", None, F.BROADCAST)
		elif child not in self.children:
			raise KeyError(child)
		else:
			self.sendMessage(child, "STOP_THREAD", None, F.BROADCAST)
		return self
		
	def pause(self, child=None):
		"""Pause self or child thread"""
		
		if not child:
			self.message("PAUSE_THREAD", None, F.BROADCAST)
		elif child not in self.children:
			raise KeyError(child)
		else:
			self.sendMessage(child, "PAUSE_THREAD", None, F.BROADCAST)
		return self
		
	def resume(self, child=None):
		"""Resume self or child thread"""
		
		if not child:
			self.message("RESUME_THREAD", None, F.BROADCAST)
		elif child not in self.children:
			raise KeyError(child)
		else:
			self.sendMessage(child, "RESUME_THREAD", None, F.BROADCAST)
		return self
		
	def join(self):
		"""thread join method."""

		self.threading.join()
		return self
		
	def createChild(self, cls, *args, **kw):
		"""Broadcast message to child"""
		
		if not issubclass(cls, Worker):
			raise TypeError("Not inherit Worker")
			
		child = cls(*args, **kw)
		return self.addChild(child)
		
	def addChild(self, *args):
		"""Add Children"""
		
		o = None
		for o in args:
			if not issubclass(type(o), Worker):
				raise TypeError("Not inherit Worker")
			if o.parent:
				raise AttributeError("Already has parent")
			o.parent = self
			self.children.add(o)
		return o
			
	def removeChild(self, *args):
		"""Remove children"""
		
		o = None
		for o in args:
			if o not in self.children:
				raise KeyError(o)
			self.children.remove(o)
			o.parent = None
		return o
		
	def waitChild(self, func, *args, **kw):
		child = self.createChild(Worker, func).start(*args, **kw)
		self.wait("CHILD_THREAD_END", child)
		if not child.error.empty():
			raise child.error.get_nowait()
		return child.ret
