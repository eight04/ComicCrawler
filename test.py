#! python3

from worker import Worker

def raiseMe(s):
	raise Exception(s)

class Main(Worker):
	def __init__(self):
		super().__init__()
		
		self.waitChild(raiseMe, "Hello error!")

Main()
