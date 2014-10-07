#! python3

class Test:
	def __init__(self):
		k = "OK"
		def test():
			nonlocal k
			k = "NO"
		def test2():
			print(k)
			
		self.test = test
		self.test2 = test2
		
t = Test()
t.test()
t.test2()
