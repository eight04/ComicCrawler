#! python3

"""Worker

A threaded worker, implemented with message queue and parent/child pattern.

The main thread should start by Worker.run(). Other threads should create and
start by Worker.start(). Every child thread needs parent or it will fail to 
start.
"""

import queue, threading, traceback, time

# class s:
	# """A data class. Define the message flags"""
	# BUBBLE = 1
	# BROADCAST = 2

class Error(Exception): pass

class WorkerError(Error): pass

class WorkerSignal(Error): pass

class StopWorker(WorkerSignal): pass

class Worker:
	"""Wrap Thread class. 
	
	Use queued message to communication between threads.
	"""
	
	def __init__(self, target=None):
		"""init"""
		
		self.error = queue.Queue()
		self.running = False
		self.printError = True
		if callable(target):
			self.worker = target
			
		self._thread = None
		self._messageBucket = queue.Queue()
		self._children = set()
		self._parent = None
		self._args = []
		self._kwargs = {}
		self._ret = None
		self._waiting = False
		self._cache = queue.Queue()
		
	def tell(self, thread, message, param=None, flag=None):
		"""Add message to other thread."""
		if not isinstance(thread, Worker):
			raise WorkerError("Thread is not inherit from Worker")
		thread.message(message, param, flag, self)
		
	def tellParent(self, message, param=None, flag=None):
		"""Shorthand to put message to parent"""
		if self._parent:
			self.tell(self._parent, message, param, flag)
		
	def bubble(self, message, param=None):
		"""Shorthand to bubble message"""
		if self._parent:
			self.tell(self._parent, message, param, "BUBBLE")
		
	def broadcast(self, message, param=None):
		"""Shorthand to broadcast message"""
		for child in self._children:
			self.tell(child, message, param, "BROADCAST")
	
	def message(self, message, param=None, flag=None, sender=None):
		"""Get message"""
		if self.running:
			self._messageBucket.put((message, param, flag, sender))
		else:
			self._transferMessage(message, param, flag, sender)
			
	def _transferMessage(self, message, param, flag, sender):
		"""Bubble and broadcast"""
		if flag is "BUBBLE" and self._parent and self._parent != sender:
			self.tellParent(message, param, flag)
			
		if flag is "BROADCAST":
			for child in self._children:
				if child != sender:
					self.tell(child, message, param, flag)
					
	def _onMessage(self, message, param, flag, sender):
		"""Message holder container, to ensure to transfer message"""
		try:
			self.onMessage(message, param, sender)
		except WorkerSignal as er:
			raise er
		except Exception as er:
			if self.printError:
				print("In onMessage,", self)
				traceback.print_exc()
			self.error.put(er)
			self.tellParent("CHILD_THREAD_ERROR", er)
		self._transferMessage(message, param, flag, sender)
		return param
	
	def onMessage(self, message, param, sender):
		"""Override"""
		if message == "STOP_THREAD":
			raise StopWorker
			
		if message == "CHILD_THREAD_START":
			self._children.add(sender)

		if message == "CHILD_THREAD_END":
			self._children.remove(sender)
			sender._parent = None
			
		if message == "CHILD_THREAD_ERROR":
			pass
			
		if message == "PAUSE_THREAD" and not self._waiting:
			self._waiting = True
			self.wait("RESUME_THREAD", sync=True)
			self._waiting = False

	def processMessage(self):
		"""Process message que untill empty"""
		while True:
			try:
				self._cache.get_nowait()
			except queue.Empty:
				break
				
		while True:
			try:
				message = self._messageBucket.get_nowait()
			except queue.Empty:
				return
			else:
				self._onMessage(*message)

	def wait(self, arg=None, sender=None, sync=False):
		"""Wait for specify message or wait specify duration.
		
		`arg` could be int or str. If `arg` is int, this function will wait 
		`arg` seconds. 
		
		If arg is str, this function will take the second param `sender`.
		If sender is provided, this function will wait till getting specify
		message `arg` which was sent by `sender`. If sender is None, this 
		function just returned after getting specify message.
		"""

		# Wait any message
		if arg is None:
			try:
				message = self._cache.get_nowait()
			except queue.Empty:
				message = self._messageBucket.get()
				self._onMessage(*message)
			return message[1]
		
		# Wait some time
		if type(arg) in [int, float]:
			while True:
				timeIn = time.time()
				try:
					message = self._cache.get_nowait()
				except queue.Empty:
					try:
						message = self._messageBucket.get(timeout=arg)
					except queue.Empty:
						return
					else:
						self._onMessage(*message)
				arg -= time.time() - timeIn
				if arg <= 0:
					return

		# Wait for message, with optional sender
		if type(arg) is str:
			while True:
				try:
					message = self._cache.get_nowait()
				except queue.Empty:
					break
				if message[0] == arg and (not sender or sender == message[3]):
					return message[1]
				
			while True:
				try:
					message = self._cache.get_nowait()
				except queue.Empty:
					message = self._messageBucket.get()
					self._onMessage(*message)
				if message[0] == arg and (not sender or sender == message[3]):
					return message[1]
				elif sync:
					self._cache.put(message)
		
	def _worker(self):
		"""Real target to pass to threading.Thread"""
		self.tellParent("CHILD_THREAD_START", self)
		
		try:
			self._ret = self.worker(*self._args, **self._kwargs)
		except StopWorker:
			pass
		except Exception as er:
			if self.printError:
				print("Something went wrong in Worker.worker")
				traceback.print_exc()
			if self.running:
				self.error.put(er)
				self.tellParent("CHILD_THREAD_ERROR", er)
			else:
				raise er
				
		# clean up
		while True:
			try:
				self.processMessage()
			except WorkerSignal:
				continue
			else:
				break
		
		self.stopAllChild()
		while self.countChild():
			try:
				self.wait("CHILD_THREAD_END")
			except WorkerSignal:
				pass

		self.running = False
		self.tellParent("CHILD_THREAD_END", self._ret)
			
	def countChild(self, running=True):
		if not running:
			return len(self._children)
			
		running = 0
		for child in self._children:
			if child.running:
				running += 1
		return running
		
	def worker(self, *args, **kwargs):
		"""Override"""
		self.wait("STOP_THREAD")
		
	def run(self, *args, **kwargs):
		"""Run as main thread"""
		self._args = args
		self._kwargs = kwargs
		self._ret = None
		
		self.running = True
		self._waiting = False
		
		self._worker()
		
		return self._ret
		
	def stopAllChild(self):
		"""Stop all child threads"""
		for child in self._children:
			if child.running:
				child.stop()

	def start(self, *args, **kwargs):
		"""call this method and self.worker will run in new thread"""
		if self.running:
			raise WorkerError("Thread is running")
			
		if not self._parent:
			raise WorkerError("Child thread don't have parent")
			
		self.running = True
		self._args = args
		self._kwargs = kwargs
		self._thread = threading.Thread(target=self._worker)
		self._thread.start()
		return self
		
	def stop(self):
		"""Stop self"""
		if self.running:
			self.message("STOP_THREAD")

	def pause(self):
		"""Pause self or child thread"""
		if self.running and not self._waiting:
			self.message("PAUSE_THREAD")

	def resume(self, child=None):
		"""Resume self or child thread"""
		self.message("RESUME_THREAD")
		
	def join(self):
		"""thread join method."""
		self._thread.join()
		return self
		
	def createChild(self, cls, *args, **kw):
		"""Create worker and add to children"""
		if not issubclass(cls, Worker):
			raise WorkerError("Not inherit Worker")
			
		child = cls(*args, **kw)
		child.setParent(self)
		return child
		
	def waitChild(self, func, *args, **kw):
		child = self.createChild(Worker, func)
		child.printError = False
		child.start(*args, **kw)
		self.wait("CHILD_THREAD_END", child)
		if not child.error.empty():
			raise child.error.get_nowait()
		return child.getRet()
		
	def getRet(self):
		"""Get return value"""
		return self._ret

	def setParent(self, thread):
		"""Add parent"""
		if self._parent:
			raise WorkerError("Already has parent")
		if not issubclass(type(thread), Worker):
			raise WorkerError("Not inherit Worker")
			
		self._parent = thread
		return self