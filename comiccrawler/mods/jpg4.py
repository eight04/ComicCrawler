#! python3

"""
https://jpg4.su/a/{id}/?sort=date_desc&page=1
"""

import re

from html import unescape

from ..episode import Episode
from ..session_manager import session_manager

domain = ["jpg4.su"]
name = "jpg4"
noepfolder = True

s = session_manager.get("https://jpg4.su/")
s.timeout = (22, 180)

def get_title(html, url):
	title = re.search(r'og:title" content="([^"]+)', html).group(1)
	return "[jpg4] {}".format(unescape(title).strip())

def get_episodes(html, url):
	# FIXME: multiple pages?
	result = []
	for match in re.finditer(r'<a href="(https://jpg4\.su/img/[^"]+)"[^>]*>\s*<img src="([^"]*)" alt="([^"]*)', html):
		ep_url, thumb, title = match.groups()
		title = re.sub(r"\.\w+$", "", title)
		image = thumb.replace(".md.", ".")
		result.append(Episode(title, ep_url, image=image))

	return result[::-1]

