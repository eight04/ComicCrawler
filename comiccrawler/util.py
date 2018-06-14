import re
import string

from .config import setting
from .io import content_write
from .profile import get as profile

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

def debug_log(*args):
	if setting.getboolean("errorlog"):
		content_write(profile("debug.log"), ", ".join(args) + "\n", append=True)

def url_extract_filename(url):
	filename = url.rpartition("/")[2]
	filename = re.sub(r"\.\w{3,4}$", "", filename)
	return filename

def clean_tags(html):
	html = re.sub("<script.+?</script>", "", html)
	html = re.sub("<.+?>", "", html)
	return html.strip()
