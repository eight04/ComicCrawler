#! python3

import sys, codecs, locale

class Test:
	encoding = "utf-8"
	

print(sys.stdout.encoding)
print(codecs.getwriter("utf-8"))
help()
print(sys.stdout.write)
writer = codecs.getwriter("utf-8")(sys.stdout)
# print(writer)
# sys.stdout

line = "ウォータールーガニ"
# line = "WAT"
# print(line)
writer.write(line)
# print("test")
# sys.stdout.write(line)
# print(line)
