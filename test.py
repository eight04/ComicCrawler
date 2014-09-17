#! python3

from worker import Worker

class Test(Worker):
	def worker:
		i = 1
		while True:
			self.wait(1)
			print(i)
			i += 1
			
test = Test().start()

while True:
	s = input()
	if s == "p":
	
