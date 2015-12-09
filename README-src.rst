Comic Crawler
=============

Comic Crawler 是用來扒圖的一支 Python
Script。擁有簡易的下載管理員、圖書館功能、 與方便的擴充能力。

Todos
-----

-  The misssion shows "updated" in mission list after re-analyze.
-  Make grabber be able to return verbose info?

20150608 更新
-------------

-  放上 PyPI，改變安裝方式
-  使用 json 儲存檔案，存檔結構改變。使用 migrate 指令可以將當下目錄的
   save.dat, library.dat 轉換成新格式。
-  更新方法︰

   -  開啟 cmd，輸入 ``pip install comiccrawler``
   -  用 cd 指令進入舊存檔的資料夾。例 ``cd /d D:\ComicCrawler-master``
   -  輸入 ``comiccrawler migrate`` 轉換存檔。
   -  輸入 ``comiccrawler gui`` 啟動，啟動完再關閉。
   -  開啟資料夾 ``%USERPROFILE%\comiccrawler``\ ，把 ``setting.ini``
      給覆蓋掉。
   -  再次輸入 ``comiccrawler gui``\ 。

      -  以後只要輸入這個指令就能啟動了

Features
--------

-  Extendible module design.
-  Easy to use function grabhtml, grabimg.
-  Auto setup referer and other common headers.

Dependencies
------------

-  pyexecjs - to execute javascript.
-  pythreadworker - a small threading library.

Development Dependencies
------------------------

-  wheel - create python wheel.
-  twine - upload package.

下載和安裝（Windows）
---------------------

Comic Crawler is on
`PyPI <https://pypi.python.org/pypi/comiccrawler/@@VERSION>`__. 安裝完
python 後，可以直接用 pip 指令自動安裝。

Install Python
~~~~~~~~~~~~~~

你需要 Python 3.4 以上。安裝檔可以從它的
`官方網站 <https://www.python.org/>`__ 下載。

安裝時記得要選「Add python.exe to path」，才能使用 pip 指令。

Install Node.js
~~~~~~~~~~~~~~~

有些網站的 JavaScript 用 Windows 內建的 Windows Script Host
會解析失敗，建議安裝 `Node.js <https://nodejs.org/>`__.

Install Comic Crawler
~~~~~~~~~~~~~~~~~~~~~

在 cmd 底下輸入以下指令︰

::

    pip install comiccrawler

更新時︰

::

    pip install --upgrade comiccrawler

Supported domains
-----------------

    @@DOMAINS

使用說明
--------

::

    Usage:
      comiccrawler domains
      comiccrawler download URL [--dest SAVE_FOLDER]
      comiccrawler gui
      comiccrawler migrate
      comiccrawler (--help | --version)

    Commands:
      domains             列出支援的網址
      download URL        下載指定的 url
      gui                 啟動主視窗
      migrate             轉換當前目錄底下的 save.dat, library.dat 成新格式

    Options:
      --dest SAVE_FOLDER  設定下載目錄（預設為 "."）
      --help              顯示幫助訊息
      --version           顯示版本

圖形介面
--------

.. figure:: http://i.imgur.com/ZzF0YFx.png
   :alt: 主視窗

   主視窗

-  在文字欄貼上網址後點「加入連結」或是按 Enter
-  若是剪貼簿裡有支援的網址，且文字欄同時是空的，程式會自動貼上
-  對著任務右鍵，可以選擇把任務加入圖書館。圖書館內的任務，在每次程式啟動時，都會檢查是否有更新。

設定檔
------

::

    [DEFAULT]
    ; 設定下載完成後要執行的程式，會傳入下載資料夾的位置
    runafterdownload =

    ; 啟動時自動檢查圖書館更新
    libraryautocheck = true

    ; 下載目的資料夾
    savepath = ~/comiccrawler/download

    ; 開啟 grabber 偵錯
    logerror = false

    ; 每隔 5 分鐘自動存檔
    autosave = 5

-  設定檔位於 ``%USERPROFILE%\comiccrawler\setting.ini``
-  執行一次 ``comiccrawler gui`` 後關閉，設定檔會自動產生

Module example
--------------

.. code:: python

    #! python3
    """
    This is an example to show how to write a comiccrawler module.

    """

    import re
    from ..core import Episode

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
        match_iter = re.finditer("<a href='(.+?)'>(.+?)</a>", html)
        episodes = []
        for match in match_iter:
            m_url, title = match.groups()
            episodes.append(Episode(title, base + m_url))
        return episodes

    """
    There are two methods to get images url. If you can get all urls from the
    first page, then use getimgurls. If you have to download each pages to get
    image url, use getimgurl and nextpage functions.

    You should only use one of two methods. Never write getimgurls and getimgurl
    both.
    """

    def getimgurls(html, url):
        """Return the list of all images"""

        match_iter = re.finditer("<img src='(.+?)'>", html)
        return [match.group(1) for match in match_iter]

    def getimgurl(html, page, url):
        """Return the url of the image"""

        return re.search("<img id='showimage' src='(.+?)'>", html).group(1)

    def getnextpageurl(page, html, url):
        """Return the url of the next page. Return None if this is the last page.
        """

        match = re.search("<a id='nextpage' href='(.+?)'>next</a>", html)
        return match and match.group(1)

    def errorhandler(er, ep):
        """Downloader will call errorhandler if there is an error happened when
        downloading image. Normally you can just ignore this function.
        """
        pass

Changelog
---------

-  2015.11.8

   -  Fix next page issue in danbooru.

-  2015.10.25

   -  Support nico seiga.
   -  Try to fix MemoryError when writing files.

-  2015.10.9

   -  Fix unicode range error in gui. See http://is.gd/F6JfjD

-  2015.10.8

   -  Fix an error that unable to skip episode in pixiv module.

-  2015.10.7

   -  Fix errors that unable to create folder if title contains "{}"
      characters.

-  2015.10.6

   -  Support search page in pixiv module.

-  2015.9.29

   -  Support http://www.chuixue.com.

-  2015.8.7

   -  Fixed sfacg bug.

-  2015.7.31

   -  Fixed: libraryautocheck option does not work.

-  2015.7.23

   -  Add module dmzj\_m. Some expunged manga may be accessed from
      mobile page.
      ``http://manhua.dmzj.com/name => http://m.dmzj.com/info/name.html``

-  2015.7.22

   -  Fix bug in module eight.

-  2015.7.17

   -  Fix episode selecting bug.

-  2015.7.16

   -  Added:

      -  Cleanup unused missions after session loads.
      -  Handle ajax episode list in seemh.
      -  Show an error if no update to download when clicking "download
         updates".
      -  Show an error if failing to load session.

   -  Changed:

      -  Always use "UPDATE" state if the mission is not complete after
         re-analyzing.
      -  Create backup if failing to load session instead of moving them
         to "invalid-save" folder.
      -  Check edit flag in MissionManager.save().

   -  Fixed:

      -  Can not download "updated" mission.
      -  Update checking will stop on error.
      -  Sankaku module is still using old method to create Episode.

-  2015.7.15

   -  Add module seemh.

-  2015.7.14

   -  Refactor: pull out download\_manager, mission\_manager.
   -  Enhance content\_write: use os.replace.
   -  Fix mission\_manager save loop interval.

-  2015.7.7

   -  Fix danbooru bug.
   -  Fix dmzj bug.

-  2015.7.6

   -  Fix getepisodes regex in exh.

-  2015.7.5

   -  Add error handler to dm5.
   -  Add error handler to acgn.

-  2015.7.4

   -  Support imgbox.

-  2015.6.22

   -  Support tsundora.

-  2015.6.18

   -  Fix url quoting issue.

-  2015.6.14

   -  Enhance ``safeprint``. Use ``echo`` command.
   -  Enhance ``content_write``. Add ``append=False`` option.
   -  Enhance ``Crawler``. Cache imgurl.
   -  Enhance ``grabber``. Add ``cookie=None`` option. Change errorlog
      behavior.
   -  Fix ``grabber`` unicode encoding issue.
   -  Some module update.

-  2015.6.13

   -  Fix ``clean_finished``
   -  Fix ``console_download``
   -  Enhance ``get_by_state``

Author
------

-  eight eight04@gmail.com
