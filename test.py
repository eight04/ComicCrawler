#! python3

from worker import Worker
from threading import Lock

class Test:
	lock = Lock()
	
test1 = Test()
test2 = Test()

print(test1.lock == test2.lock)
