#! python3

from worker import Worker

class Test(Worker):
	def worker(self):
		i = 1
		while True:
			print(i)
			self.wait(1)
			i += 1
			
test = Test().start()
while True:
	s = input()
	if s == "p":
		test.pause()
	if s == "r":
		test.resume()
	if s == "q":
		test.stop()
		break
	if s == "s":
		test.stop()
	if s == "e":
		print(test.error.empty() or test.error.get_nowait())
	if s == "rs":
		test.start()
