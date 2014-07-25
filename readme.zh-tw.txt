Comic Crawler Readme v.20140726


使用需求:
==========================
Python 3.4 up
	下載網站︰
	https://www.python.org/
	
	記得要選「Add python.exe to path」，否則安裝 PyExecJS 時會找不到 pip 命令。
	
PyExecJS
	1. 先安裝完 Python
	2. 按 Windows + R，輸入 cmd 後按 Enter
	3. 輸入 pip install pyexecjs 後按 Enter。安裝時應該會跑出類似︰
		====
		Downloading/unpacking pyexecjs
		  Downloading PyExecJS-1.0.4.tar.gz
		  Running setup.py (path:C:\User.......

		Installing collected packages: pyexecjs
		  Running setup.py install for pyexecjs

		Successfully installed pyexecjs
		Cleaning up...
		====
	4. 安裝完畢
	
	
目前支援網址
======================
comic.ck101.com www.pixiv.net www.99comic.com manhua.dmzj.com 
deviantart.com www.8comic.com konachan.com www.dm5.com 
comic.sfacg.com 

	
使用方法︰
==========================
下載︰
	執行comiccrawlergui.py，貼上連結後點「加入連結」，
	若是程式支援的網址，在復製完後切換到 Comic Crawler 的視窗就會自動貼上。
	貼上後按 Enter 也可以加入連結。
	加入連結後點「開始下載」就會自動下載到指定資料夾中了。
	
圖書館︰
	對著任務右鍵，可以選擇把任務加入圖書館。
	圖書館內的任務，在每次程式啟動時，都會檢查是否有更新。
	也可以手動點選「檢查更新」。
	點「下載更新」會把顯示「有更新」的任務加到下載列表裡面（不會自動下載哦！）。

設定檔（setting.ini）︰
	第一次執行程式時會在同目錄下產生 setting.ini，可以設定...
		savepath，設定下載目錄。
		runafterdownload，可以設定下載完後欲呼叫的程式，會傳入任務資料夾位置。
		
	zip.bat是預先寫好的Windows批次檔，會呼叫7z命令將檔案壓縮後刪除資料夾（小心！）
	與runafterdownload配合使用。
	
	什麼是7z？它是個又小又快的壓縮軟體︰
		http://www.developershome.com/7-zip/

其它︰
	在 Windows 上可以執行 winlaunch.pyw，不會顯示 cmd。
	
	因為下載時會根據任務名稱來建立下載資料夾，若有任務名稱相同的情況，
	後下載的任務會因為已經下載過了而忽略下載。
	若遇到這種狀況，建議把任務改名（選擇任務後按右鍵->改名）。
	
	下載後會檢查圖片格式是否正確。
	

====================================
有發現任意 bug 歡迎寄 email 給我或到 PTT 留言！
最近有在練習用 Github，也可以試試上面的 Issue Tracker︰
	https://github.com/eight04/ComicCrawler


聯絡作者︰
==========================
eight04@gmail.com


