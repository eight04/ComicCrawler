Comic Crawler
=============

Comic Crawler 是用來扒圖的一支 Python Script。擁有簡易的下載管理員、圖書館功能、
與方便的擴充能力。

Features
--------
* Extendible module design.
* Easy to use function grabhtml, grabimg.
* Auto setup referer and other common headers.

This branch is for up coming update.

Rewrite
-------
* Use threadworker.
* Distribute as package and upload to PyPI.
* Save missions in pool.

Structure
---------
- ComicCrawlerGUI
	- DownloadManager
		- Analyzer
		- Downloader
		- ModuleManager
			- ModPool
		- MissionManager
			- SaveFile
			- MissionPool
			- ViewList1
			- ViewList2

Todos
-----
* Can't add url during library analyzing?
* After library analyze shouldn't show select ep dialog.
* Move `mission` param from `downloadWorker.__init__` to `.worker`.
* Set worker parent in __init__.

Next major update
-----------------
* Stop using pickle and remove mission_container.
* Move saving/loading data to higher level.
* Use `with` to deal with lock.
* Use new [pyWorker](https://github.com/eight04/pyWorker).

下載和安裝（Windows）
-------------------

### Python

你需要 Python 3.4 以上。安裝檔可以從它的[官方網站](https://www.python.org/)下載。
	
安裝時記得要選「Add python.exe to path」，否則安裝 PyExecJS 時會找不到 `pip` 命令。
	
### PyExecJS

[PyExecJS](https://pypi.python.org/pypi/PyExecJS) 是 Python 的套件，用來執行 JavaScript。裝完 Python 後在 cmd 底下直接用 pip 指令

	pip install pyexecjs
	
### Comic Crawler

直接從 Github 下載原始碼就能執行了。點右方的「Download ZIP」按鈕。

## 目前支援網址

> chan.sankakucomplex.com, www.pixiv.net, comic.sfacg.com, www.example.com, exhentai.org, comic.example.com, www.comicvip.com, danbooru.donmai.us, manhua.dmzj.com, deviantart.com, tel.dm5.com, g.e-hentai.org, comic.acgn.cc, www.dm5.com, konachan.com, comic.ck101.com, www.8comic.com, www.99comic.com

## 命令介面

Comic Crawler 的核心就是個可以載入 module 的扒圖工具。基本命令只有兩個。

### 列出支援的網址

	comiccrawler.py domains

### 下載網址內的漫畫至特定目錄

	comiccrawler.py download URL -d FILE_PATH

## 圖形介面

### 下載

執行comiccrawlergui.py，貼上連結後點「加入連結」，若是程式支援的網址，在復製完後切換到 Comic Crawler 的視窗就會自動貼上。貼上後按 Enter 也可以加入連結。加入連結後點「開始下載」就會自動下載到指定資料夾中了。

### 圖書館

對著任務右鍵，可以選擇把任務加入圖書館。圖書館內的任務，在每次程式啟動時，都會檢查是否有更新。也可以手動點選「檢查更新」。點「下載更新」會把顯示「有更新」的任務加到下載列表裡面，並自動開始下載。

### 設定檔（setting.ini）

第一次執行程式時會在同目錄下產生 setting.ini，可以設定...

	savepath = 下載目錄。
	runafterdownload = 下載完後欲呼叫的程式，會傳入任務資料夾位置。
	libraryautocheck = 是否要自動檢查圖書館更新

`zip.bat` 是預先寫好的 Windows 批次檔，會呼叫 7z 命令將檔案壓縮後刪除資料夾（小心！）。與 `runafterdownload` 配合使用。

Module example
--------------
```python
#! python3
"""
This is an example to show how to write a comiccrawler module.

"""

import re
import comiccrawler.core

# The header used in grabber method
header = {}

# Match domain
domain = ["www.example.com", "comic.example.com"]

# Module name
name = "This Is an Example"

# With noepfolder = True, Comic Crawler won't generate subfolder for each episode.
noepfolder = False

# Wait 5 seconds between each page
rest = 5

# Specific user settings
config = {
	"user": "user-default-value",
	"hash": "hash-default-value"
}

def loadconfig():
	"""This function will be called each time the config reloaded.
	"""
	header["Cookie"] = "user={}; hash={}".format(config["user"], config["hash"])

def gettitle(html, url):
	"""Return mission title.
	
	Title will be used in saving filepath, so be sure to avoid duplicate title.
	"""
	return re.search("<h1 id='title'>(.+?)</h1>", html).group(1)
	
def getepisodelist(html, url):
	"""Return episode list.
	
	The episode list should be sorted by date, latest at last, so the 
	downloader will download the oldest first.
	"""
	base = re.search("(https?://[^/]+)", url).group(1)
	ms = re.findall("<a href='(.+?)'>(.+?)</a>", html)
	s = []
	for m in ms:	
		u, title = m
		e = comiccrawler.Episode()
		e.title = title
		e.firstpageurl = base + url
		s.append(e)
	return s

"""
There are two methods to get images url. If you can get all urls from the 
first page, then use getimgurls. If you have to download each pages to get
image url, use getimgurl and nextpage functions.

Note that you should only implement one of two methods. Never write 
getimgurls and getimgurl both.
"""

def getimgurls(html, url):
	"""Return the list of all images"""
	
	ms = re.findall("<img src='(.+?)'>", html)
	return [m[0] for m in ms]
	
def getimgurl(html, page, url):
	"""Return the url of the image"""
	
	return re.search("<img id='showimage' src='(.+?)'>", html).group(1)
	
def getnextpageurl(page, html, url):
	"""Return the url of the next page. Return '' if this is the last page.
	"""
	
	r = re.search("<a id='nextpage' href='(.+?)'>next</a>", html)
	if r is None:
		return ""
	return r.group(1)
		
def errorhandler(er, ep):
	"""Downloader will call errorhandler if there is an error happened when
	downloading image. Normally you can just ignore this function.
	"""
	pass
```

Contributors
------------
* eight <eight04@gmail.com>
