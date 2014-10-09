# Comic Crawler Readme v.20140726

Comic Crawler 是用來扒圖的一支 Python Script。擁有簡易的下載管理員、圖書館功能、與方便的擴充能力。

## 下載和安裝（Windows）

### Python

你需要 Python 3.4 以上。安裝檔可以從它的[官方網站](https://www.python.org/)下載。
	
安裝時記得要選「Add python.exe to path」，否則安裝 PyExecJS 時會找不到 `pip` 命令。
	
### PyExecJS

[PyExecJS](https://pypi.python.org/pypi/PyExecJS) 是 Python 的套件，用來執行 JavaScript。裝完 Python 後在 cmd 底下直接用 pip 指令

	pip install pyexecjs
	
### Comic Crawler

目前的 Release 都放在 [Google Drive](http://x.co/54nww)，直接將壓縮檔下載後解壓縮就可以了。

## 目前支援網址

> comic.ck101.com www.pixiv.net www.99comic.com manhua.dmzj.com deviantart.com www.8comic.com konachan.com www.dm5.com comic.sfacg.com 

## 命令介面

Comic Crawler 的核心就是個可以載入 module 的扒圖工具。基本命令只有兩個。

### 列出支援的網址

	comiccrawler.py domains

### 下載網址內的漫畫至特定目錄

	comiccrawler.py download URL -d FILE_PATH

## 圖形介面

圖形介面是以 Tkinter 寫成的，詳細可以參考 readme.zh-tw.txt。

## Todos

* move removeLibDup to controller
* Change implemention to threaded:
	- dm5, deviant, ck101, sfacg, sankaku, pixiv, konachan
* Change implemention of mission and ep?

## 聮絡作者

eight04@gmail.com


