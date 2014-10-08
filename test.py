#! python3

from collections import OrderedDict

t = OrderedDict()
t["test"] = "OK"
t["test2"] = "NO"

for key in t.items():
	print(key)
