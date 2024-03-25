import re
import string
from functools import total_ordering
from pathlib import Path

import uncurl

def dump(html):
	Path("dump.html").write_text(html, encoding="utf-8")

def extract_curl(cmd):
	if not cmd:
		raise ValueError("Empty curl")
	try:
		context = uncurl.parse_context(cmd)
	except SystemExit:
		raise ValueError(f"Failed parsing curl: {cmd}") from None
	return context.url, context.headers, context.cookies

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
		c: None for c in set(chr(i) for i in range(128)).difference(string.printable)
		})
	table.update({
		chr(i): " " for i in range(32) if chr(i) not in table
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

def url_extract_filename(url):
	filename = url.rpartition("/")[2]
	filename = re.sub(r"\.\w{3,4}$", "", filename)
	return filename

def clean_tags(html):
	html = re.sub("<script.+?</script>", "", html)
	html = re.sub("<.+?>", "", html)
	html = re.sub(r"\s+", " ", html)
	return html.strip()

@total_ordering	
class MinimumAny:
	def __le__(self, other):
		return True

	def __eq__(self, other):
		return self is other

MIN = MinimumAny()

def balance(s: str, index: int, left="(", right=")", skip=0):
	"""Return the string inside (including) matched left and right brackets."""
	# backward search
	count = 0
	for i in range(index, -1, -1):
		if s[i] == right:
			count += 1
		elif s[i] == left:
			if count == -skip:
				break
			count -= 1
	else:
		raise ValueError(f"Unbalanced brackets: {s}")
	start = i

	# forward search
	count = 0
	for j in range(index, len(s)):
		if s[j] == left:
			count += 1
		elif s[j] == right:
			if count == -skip:
				break
			count -= 1
	else:
		raise ValueError(f"Unbalanced brackets: {s}")
	end = j + 1

	return s[start:end]

