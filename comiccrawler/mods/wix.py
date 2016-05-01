#! python3

"""this is Wix module for comiccrawler	

FIXME: Since wix actually is not a image hosting site. The update checking
won't work if there are updates in each pages, i.e. Comic Crawler dosn't run
through each pages to check for image update.
"""

import re
import json

from urllib.parse import urljoin
from ..core import Episode, grabhtml

domain = ["wix.com"]
name = "Wix"

def get_title(html, url):
	return "[Wix.com] " + re.search("<title>([^<]+)", html).group(1)
	
def get_episodes(html, url):
	public_model = re.search("var publicModel = ({.+})", html).group(1)
	public_model = json.loads(public_model)
	
	pages = public_model["pageList"]["pages"]
	
	s = []
	
	for page in pages:
		page_url = "{url}#!{seo}/{id}".format(
			url=url,
			seo=page["pageUriSEO"],
			id=page["pageId"]
		)
		s.append(Episode(page["pageUriSEO"], page_url))
	
	return s

def get_images(html, url):
	public_model = re.search("var publicModel = ({.+})", html).group(1)
	public_model = json.loads(public_model)
	
	id = re.search("[^/]+$", url).group()
	
	pages = public_model["pageList"]["pages"]
	
	for page in pages:
		if page["pageId"] == id:
			break
	else:
		raise Exception("Can't find pageId {}".format(id))
	
	json_url = page["urls"][0]
	data = grabhtml(json_url)
	data = json.loads(data)
	data = data["data"]["document_data"]
	
	return [
		"https://static.wixstatic.com/media/" + item["uri"] 
			for item in data.values()
				if item["type"] == "Image"
	]
