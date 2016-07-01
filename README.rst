Comic Crawler
=============

Comic Crawler 是用來扒圖的一支 Python Script。擁有簡易的下載管理員、圖書館功能、 與方便的擴充能力。

2016.6.4 更新
--------------

-  此版本修改了存檔的運作方式，建議在更新前先將存檔備份
-  改版後，所有「未使用中」的任務資料會存到 ``~/comiccrawler/pool/`` 資料夾
-  ``~/comiccrawler/pool.json`` 不再儲存 episode 相關資訊
-  任務下載時，會再從 pool 資料夾中讀出 episode 相關資訊
-  目的為減少不必要的記憶體使用量

2016.2.27 更新
--------------

-  "www.comicvip.com" 被 "www.comicbus.com" 取代。詳細請參考 `#7 <https://github.com/eight04/ComicCrawler/issues/7>`__

Dependencies
------------

-  docopt - command line interface.
-  pyexecjs - to execute javascript.
-  pythreadworker - a small threading library.
-  safeprint - to print unicode chars on Windows.
-  requests - http library.

Development Dependencies
------------------------

-  wheel - create python wheel.
-  twine - upload package.
-  docutils - to test rst.
-  pyxcute - task runner.

下載和安裝（Windows）
---------------------

Comic Crawler is on
`PyPI <https://pypi.python.org/pypi/comiccrawler/>`__. 安裝完
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

.. DOMAINS
..

    chan.sankakucomplex.com comic.acgn.cc comic.ck101.com comic.sfacg.com danbooru.donmai.us deviantart.com exhentai.org g.e-hentai.org ikanman.com imgbox.com konachan.com m.dmzj.com manhua.dmzj.com seiga.nicovideo.jp tel.dm5.com tsundora.com tumblr.com tw.seemh.com wix.com www.8comic.com www.99comic.com www.buka.cn www.chuixue.com www.comicbus.com www.comicvip.com www.dm5.com www.facebook.com www.iibq.com www.manhuadao.com www.pixiv.net www.seemh.com yande.re

.. END DOMAINS

使用說明
--------

As a CLI tool:

::

    Usage:
      comiccrawler domains
      comiccrawler download URL [--dest SAVE_FOLDER]
      comiccrawler gui
      comiccrawler (--help | --version)

    Commands:
      domains             列出支援的網址
      download URL        下載指定的 url
      gui                 啟動主視窗

    Options:
      --dest SAVE_FOLDER  設定下載目錄（預設為 "."）
      --help              顯示幫助訊息
      --version           顯示版本
      
or you can use it in your python script:

.. code:: python

    from comiccrawler.core import Mission, analyze, download
    
    # create a mission
    m = Mission(url="http://example.com")
    analyze(m)
    
    # select the episodes you want
    for ep in m.episodes:
        if ep.title != "chapter 123":
            ep.skip = True
    
    # download to savepath
    download(m, "path/to/save")
    
圖形介面
--------

.. figure:: http://i.imgur.com/ZzF0YFx.png
   :alt: 主視窗

-  在文字欄貼上網址後點「加入連結」或是按 Enter
-  若是剪貼簿裡有支援的網址，且文字欄同時是空的，程式會自動貼上
-  對著任務右鍵，可以選擇把任務加入圖書館。圖書館內的任務，在每次程式啟動時，都會檢查是否有更新。

設定檔
------

::

    [ComicCrawler]
    ; 設定下載完成後要執行的程式，會傳入下載資料夾的位置
    runafterdownload =

    ; 啟動時自動檢查圖書館更新
    libraryautocheck = true

    ; 下載目的資料夾
    savepath = ~/comiccrawler/download

    ; 開啟 grabber 偵錯
    errorlog = false

    ; 每隔 5 分鐘自動存檔
    autosave = 5

-  設定檔位於 ``%USERPROFILE%\comiccrawler\setting.ini``
-  執行一次 ``comiccrawler gui`` 後關閉，設定檔會自動產生
-  各別的網站會有自己的設定，通常是要填入一些登入相關資訊
-  設定檔會在重新啟動後生效。若 ComicCrawler 正在執行中，可以點「重載設定檔」來載入新設定

runafterdownload
~~~~~~~~~~~~~~~~

-  `Pixiv Ugoku to MP4 <https://github.com/eight04/bunch-of-shells/tree/master/Pixiv%20Ugoku%20to%20MP4>`__

Module example
--------------

Starting from version 2016.4.21, you can add your own module to ``~/comiccrawler/mods/module_name.py``.

.. code:: python

    #! python3
    """
    This is an example to show how to write a comiccrawler module.

    """

    import re
    from urllib.parse import urljoin
    from comiccrawler.core import Episode

    # The header used in grabber method
    header = {}
    
    # The cookies
    cookie = {}

    # Match domain. Support sub-domain, which means "example.com" will match
    # "*.example.com"
    domain = ["www.example.com", "comic.example.com"]

    # Module name
    name = "Example"

    # With noepfolder = True, Comic Crawler won't generate subfolder for each
    # episode.
    noepfolder = False

    # Wait 5 seconds between each download.
    rest = 5

    # Specific user settings
    config = {
        "user": "user-default-value",
        "hash": "hash-default-value"
    }

    def load_config():
        """This function will be called each time the config reloaded.
        
        The user might put additional info into config, so it is not recommended
        to use dict.update directly, which will leak personal info to the 
        website.
        """
        cookie["user"] = config["user"]
        cookie["hash"] = config["hash"]

    def get_title(html, url):
        """Return mission title.

        Title will be used in saving filepath, so be sure to avoid duplicate title.
        """
        return re.search("<h1 id='title'>(.+?)</h1>", html).group(1)

    def get_episodes(html, url):
        """Return episode list.

        The episode list should be sorted by date, oldest first.
        If the episode list is multi-pages, specify the url of next page in
        get_next_page.
        """
        match_list = re.findall("<a href='(.+?)'>(.+?)</a>", html)
        return [Episode(title, urljoin(url, ep_url))
                for ep_url, title in match_list]

    def get_images(html, url):
        """Get the URL of all images.
        
        The result could be:

        -  A list of image URL.
        -  A generator yielding image URL.
        -  An image URL, when there is only one image in current page.
        
        An `image URL` means the URL string of the image or a callback function
        which returns the URL of the image.
        
        If the episode has multi-pages, specify the url of next page in
        get_next_page.
        
        Use generator in caution! If your generator raised any error between
        two images, next call to the generator will always result in
        StopIteration, which means that Comic Crawler will think it had crawled
        all images and navigate to next page. If you need to use grabhtml()
        between each pages (i.e. may raise HTTPError), you should return a list
        of callback!
        """
        return re.findall("<img src='(.+?)'>", html)

    def get_next_page(html, url):
        """Return the url of the next page."""
        match = re.search("<a id='nextpage' href='(.+?)'>next</a>", html)
        if match:
            return match.group(1)

    def errorhandler(error, episode):
        """Downloader will call errorhandler if there is an error happened when
        downloading image. Normally you can just ignore this function.
        """
        pass
        
    def imagehandler(ext, b):
        """If this function exist, Comic Crawler will call it before saving
        image to disk, letting the module be able to edit the image.
        
        @ext  A str of image extension. Including "." (e.g. ".jpg")
        @b    The bytes object of the image.

        It should return a (result_ext, result_b) tuple.
        """
        return (ext, b)
        
Todos
-----

-  Make grabber be able to return verbose info?
-  Need a better error log system.
-  Support pool in Sankaku.
-  Add module.get_episode_id to make the module decide how to compare episodes.

Changelog
---------

-  2016.7.1

   -  Use cross-platform startfile (incomplete).
   -  Use `clam` theme for GUI under linux.
   -  Fix the error message of update checking failure.
   -  Update checking won't block GUI thread anymore.
   -  Update `pythreadworker` to 0.6.
   -  Fix import syntax in `gui.get_scale`.

-  2016.6.30

   -  Support high dpi displays.
   -  Don't show error in library thread. Only warn the user when update checking fails.

-  2016.6.25

   -  API changed. Now the errorhandler will recieve ``(error, crawler)`` instead of ``(error, episode)``.
   -  Add errorhandler in seemh. It will try to use different host if downloading failed.
   -  Drop mission to the bottom when update checking failed. Update checking process will stop if it had retried 10 times.

-  2016.6.14.1

   -  Pass pyflakes and fix a bunch of typo.

-  2016.6.14

   -  Fix: always re-init in crawlpage loop!

-  2016.6.12

   -  Use GBK instead of GB2312 in grabber.
   -  Add the ability to get title from non-user page in nico.
   -  Fix: unable to add mission in chuixue.
   -  Fix: unable to download image in nico.
   -  Fix: episode is lost after changing the name of the mission.
   -  Fix: unable to recheck update after login error.

-  2016.6.10

   -  Change how to handle HTTP 429 error. Let the mission drop.
   -  Add login check in sankaku.
   -  Support .jpe(.jpg), .webm file types.

-  2016.6.4

   -  Change how saved data works. Comic Crawler will write inactive mission data into ``~/comiccrawler/pool/`` folder to save the memory.
   -  Fix regex in dA.
   -  Fix sankaku's hang. Do not suppress 429 error in grabber.

-  2016.6.3

   -  Minor change to save/load file function to avoid unnecessary copy.
   -  Comic Crawler will now execute `runafterdownload` command both from the default section and the module section.

-  2016.5.30

   -  Add module.imagehandler, which can edit the image file before saving to disk.
   -  Write frame info into ugoku zip in pixiv.

-  2016.5.28

   -  Change how config work. Now you can specify different setting in each sections. (e.g. use different savepath with different module)
   -  Save frame info about ugoku in pixiv.
   -  Drop config.update in module.load_config.
   -  Try to support additional info in get_images.

-  2016.5.24

   -  Support buka.

-  2016.5.20

   -  Find server by executing js in seemh.

-  2016.5.15

   -  Fix dependency scheme.

-  2016.5.2

   -  Use `Conten-Type` header to guess file extension.
   -  Fix a bug that the thread is not removed when recived DOWNLOAD_INVALID.
   -  Pause download when meeting 509 error in exh.
   -  Add .mp4 to valid file types.

-  2016.5.1.1

   -  Fix a bug that Comic Crawler doesn't retry when the first connection failed.
   -  Add `Episode.image`, so the module can supply image list during constructing Episode.

-  2016.5.1

   -  Support wix.com.

-  2016.4.27

   -  Domain changed in seemh.

-  2016.4.26.1

   -  Fix charset encoding bug.

-  2016.4.26

   -  Fix config bug with upper-case key.
   -  Check urls of old episodes to avoid unnecessary analyzing.
   -  Add option to get original image in exh. It will cost 5x of viewing limit.

-  2016.4.22.3

   -  Fix retry-after hanged bug.
   -  Fix cnfig override bug. Use ``ComicCrawler`` section to replace ``DEFAULT`` section.
   -  Support account login in sankaku.
   -  Support HTTP error log before raising.
   -  Show next page url while analyzing.

-  2016.4.22.2

   -  Move to pythreadworker 0.5.0

-  2016.4.22.1

   -  Support loading module in python3.4.

-  2016.4.22

   -  Fix setup.py. Use find_packages.

-  2016.4.21

   -  Big rewrite.
   -  Move to requests.
   -  Move to pythreadworker 0.4.0.
   -  Add the ability to load module from ``~/comiccrawler/mods``
   -  Drop migrate command.

-  2016.4.20

   -  Update install_requires.

-  2016.4.13

   -  Fix facebook bug.
   -  Move to doit.

-  2016.4.8

   -  Fix get_next_page error.
   -  Fix key error in CLI.

-  2016.4.4

   -  Use new API!
   -  Analyzer will check the last episode to decide whether to analyze all pages.
   -  Support multiple images in one page.
   -  Change how getimgurl and getimgurls work.

-  2016.4.2

   -  Add tumblr module.
   -  Enhance: support sub-domain in ``mods.get_module``.

-  2016.3.27

   -  Fix: handle deleted post (konachan).
   -  Fix: enhance dialog. try to fix `#8 <https://github.com/eight04/ComicCrawler/issues/8>`__.

-  2016.2.29

   -  Fix: use latest comicview.js (8comic).

-  2016.2.27

   -  Fix: lastcheckupdate doesn't work.
   -  Add: comicbus domain (8comic).

-  2016.2.15.1

   -  Fix: can not add mission.

-  2016.2.15

   -  Add `lastcheckupdate` setting. Now the library will only automatically check updates once a day.
   -  Refactor. Use MissionProxy, Mission doesn't inherit UserWorker anymore.

-  2016.1.26

   -  Change: checking updates won't affect mission which is downloading.
   -  Fix: page won't skip if the savepath contains "~".
   -  Add: a new url pattern in facebook.

-  2016.1.17

   -  Fix: an url matching issue in Facebook.
   -  Enhance: downloader will loop through other episodes rather than stop current mission on crawlpage error.

-  2016.1.15

   -  Fix: ComicCrawler doesn't save session during downloading.

-  2016.1.13

   -  Handle HTTPError 429.

-  2016.1.12

   -  Add facebook module.
   -  Add ``circular`` option in module. Which should be set to ``True`` if downloader doesn't know which is the last page of the album. (e.g. Facebook)

-  2016.1.3

   -  Fix downloading failed in seemh.

-  2015.12.9

   -  Fix build-time dependencies.

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

   -  Fix errors that unable to create folder if title contains "{}" characters.

-  2015.10.6

   -  Support search page in pixiv module.

-  2015.9.29

   -  Support http://www.chuixue.com.

-  2015.8.7

   -  Fixed sfacg bug.

-  2015.7.31

   -  Fixed: libraryautocheck option does not work.

-  2015.7.23

   -  Add module dmzj\_m. Some expunged manga may be accessed from mobile page. ``http://manhua.dmzj.com/name => http://m.dmzj.com/info/name.html``

-  2015.7.22

   -  Fix bug in module eight.

-  2015.7.17

   -  Fix episode selecting bug.

-  2015.7.16

   -  Added:

      -  Cleanup unused missions after session loads.
      -  Handle ajax episode list in seemh.
      -  Show an error if no update to download when clicking "download updates".
      -  Show an error if failing to load session.

   -  Changed:

      -  Always use "UPDATE" state if the mission is not complete after re-analyzing.
      -  Create backup if failing to load session instead of moving them to "invalid-save" folder.
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
   -  Enhance ``grabber``. Add ``cookie=None`` option. Change errorlog behavior.
   -  Fix ``grabber`` unicode encoding issue.
   -  Some module update.

-  2015.6.13

   -  Fix ``clean_finished``
   -  Fix ``console_download``
   -  Enhance ``get_by_state``

Author
------

-  eight eight04@gmail.com
