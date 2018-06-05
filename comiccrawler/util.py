import string

def create_safefilepath_table():
	table = {}
	table.update({
		"/": "／",
		"\\": "＼",
		"?": "？",
		"|": "｜",
		"<": "＜",
		">": "＞",
		":": "：",
		"\"": "＂",
		"*": "＊"
	})
	table.update({
		c: None for c in set([chr(i) for i in range(128)]).difference(string.printable)
	})
	return str.maketrans(table)
	
safefilepath_table = create_safefilepath_table()
dot_table = str.maketrans({".": "．"})

def safefilepath(s):
	"""Return a safe directory name."""
	s = s.strip().translate(safefilepath_table)
	if s[-1] == ".":
		s = s.translate(dot_table)
	return s
