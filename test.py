#! python3

from worker import Worker
from threading import Lock

class Test:
	name = "test1"


class Test2(Test):
	name = "test2"
	def showName(self):
		print(super())
	
test = Test2()
test.showName()
