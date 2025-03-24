import enlighten
from worker import listen

from ..channel import request_ch

class CLIProgress:
	def __init__(self):
		self.pb_manager = enlighten.get_manager()
		self.pb: dict[int, enlighten.Counter] = {}
		request_ch.sub()

		@listen("REQUEST_START")
		def on_request_start(event):
			self.pb[event.data.id] = self.pb_manager.counter(total=event.data.total, desc=event.data.hostname, unit="B", leave=False)
			self.pb[event.data.id].update(event.data.loaded - self.pb[event.data.id].count)

		@listen("REQUEST_PROGRESS")
		def on_request_progress(event):
			self.pb[event.data.id].update(event.data.loaded - self.pb[event.data.id].count)

		@listen("REQUEST_END")
		def on_request_end(event):
			self.pb[event.data.id].close()
			del self.pb[event.data.id]
		
