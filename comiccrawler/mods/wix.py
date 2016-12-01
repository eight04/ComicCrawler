#! python3

"""this is Wix module for comiccrawler
"""

import re
import json

from ..core import Episode, grabhtml

domain = ["wix.com"]
name = "Wix"
noepfolder = True

def get_title(html, url):
	return "[Wix.com] " + re.search("<title>([^<]+)", html).group(1)
	
def trim_ext(text):
	return re.sub("\.(gif|png|jpg)$", "", text, flags=re.I).strip()
	
def get_episodes(html, url):
	public_model = re.search("var publicModel = ({.+})", html).group(1)
	public_model = json.loads(public_model)
	
	pages = public_model["pageList"]["pages"]
	
	s = []
	
	for page in pages:
		try:
			data = grabhtml(page["urls"][0])
		except KeyError:
			data = grabhtml("https://static.wixstatic.com/sites/" + page["pageJsonFileName"] + ".z?v=3")
		
		data = json.loads(data)
		data = data["data"]["document_data"]
		
		for item in data.values():
			if item["type"] != "Image":
				continue
			s.append(Episode(
				"{} - {}".format(page["title"], trim_ext(item.get("title", "")) or item["id"])		,
				"https://static.wixstatic.com/media/" + item["uri"],
				image="https://static.wixstatic.com/media/" + item["uri"]
			))
			
	return s
