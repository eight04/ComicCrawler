#! python3

"""Comic Crawler GUI.

"""

from tkinter import *
from tkinter.ttk import *
from functools import partial

import sys, os, webbrowser, worker
import tkinter.messagebox as messagebox

from . import config, mods, DownloadManager
from .safeprint import safeprint, addcallback as sp_addcallback, removecallback as sp_removecallback
from .core import safefilepath

STATE = {
	"INIT": "準備",
	"ANALYZED": "解析完成",
	"DOWNLOADING": "下載中",
	"PAUSE": "停止",
	"FINISHED": "完成",
	"ERROR": "錯誤",
	"INTERRUPT": "已刪除",
	"UPDATE": "有更新",
	"ANALYZING": "分析中",
	"ANALYZE_INIT": "準備分析"
}

class Dialog(Toplevel):
	"""Dialog class"""
	
	def __init__(self, parent, title=None):
		"""Create some base method and elements"""
		
		super().__init__(parent)
		
		# body
		if title:
			self.title(title)
		self.parent = parent
		self.result = None
		
		self.body = Frame(self)
		self.body.pack()
		
		# button bar
		box = Frame(self)
		Button(box, text="確定", command=self.ok, default=ACTIVE).pack(side="left")
		Button(box, text="取消", command=self.cancel).pack(side="left")
		box.pack()
		self.buttonbox = box

		# bind event
		self.bind("<Return>", self.ok)
		self.bind("<Escape>", self.cancel)
		
		# show dialog and disable parent
		self.grab_set()
		self.protocol("WM_DELETE_WINDOW", self.cancel)
		self.focus_set()

	def ok(self, event=None):
		"""When you press ok"""

		if not self.validate():
			self.initial_focus.focus_set() # put focus back
			return

		self.withdraw()
		self.update_idletasks()

		self.apply()
		self.cancel()

	def cancel(self, event=None):
		"""When you press cancel"""

		# put focus back to the parent window
		self.parent.focus_set()
		self.destroy()

	def validate(self):
		"""overwrite with your validate method here"""
		
		return 1

	def apply(self):
		"""overwrite with your post data method"""
		
		pass

	def wait(self):
		"""wait the dialog to close"""
		
		self.wait_window(self)
		return self.result
	
class MainWindow(worker.UserWorker):
	"""Main GUI window class."""
	
	def worker(self):
		"""Main window worker"""
		self.register_message()
		self.init()
		self.create_view()
		self.bindevent()
		self.mainloop()
		self.uninit()
		
	def init(self):
		"""Create mission downloader"""
		sp_addcallback(self.sp_callback)
		
		self.downloader = self.create_child(DownloadManager).start()
		self.cid_view = {}
		self.cid_library = {}
		
		# Work with clipboard
		self.pre_url = None
		
	def mainloop(self):
		"""Main loop, including gtk and worker"""
		self.root.after(100, self.tkloop)
		self.root.mainloop()
		
	def uninit(self):
		"""Remove safeprint callback"""
		sp_removecallback(self.sp_callback)
		
	def get_cid(self, cid_index, mission):
		"""Get matched cid from cid index"""
		for cid, mission2 in cid_index.items():
			if mission2 is mission:
				return cid
				
	def update_mission_info(self, tv, cid, mission):
		"""Update mission info on treeview"""
		tv.set(cid, "state", STATE[mission.state])
		tv.set(cid, "name", mission.title)
	
	def register_message(self):
		"""Add listeners"""
		@self.listen("LOG_MESSAGE")
		def dummy(text):
			text = text.splitlines()[-1]
			self.statusbar["text"] = text
	
		@self.listen("MISSION_PROPERTY_CHANGED")
		def dummy(mission):
			cid = self.get_cid(self.cid_view, mission)
			if cid is not None:
				self.update_mission_info(self.tv_view, cid, mission)
			
			cid = self.get_cid(self.cid_library, mission)
			if cid is not None:
				self.update_mission_info(self.tv_library, cid, mission)
			
		@self.listen("MISSION_LIST_REARRANGED")
		def dummy(que):
			if que == self.downloader.mission_manager.view:
				self.tv_refresh("view")
			if que == self.downloader.mission_manager.library:
				self.tv_refresh("library")
			
		@self.listen("AFTER_ANALYZE")
		def dummy(mission):
			if len(mission.episodes) == 1 or select_episodes(self.root, mission):
				self.downloader.mission_manager.add("view", mission)
			
		@self.listen("AFTER_ANALYZE_FAILED")
		def dummy(param):
			mission, error = param
			messagebox.showerror(
				mission.module.name,
				"解析錯誤！\n{}".format(error)
			)
			
		@self.listen("MISSION_POOL_LOAD_FAILED")
		def dummy(param):
			messagebox.showerror(
				"Comic Crawler",
				"讀取存檔失敗！移至 {}\n{}".format(*param)
			)
				
	def create_view(self):
		"""Draw the window."""
		self.root = Tk()
		
		self.root.title("Comic Crawler")
		self.root.geometry("500x400")
		
		Label(self.root,text="輸入連結︰").pack(anchor="w")
		
		# url entry
		entry_url = Entry(self.root)
		entry_url.pack(fill="x")
		self.entry_url = entry_url
		
		# bunch of buttons
		buttonbox = Frame(self.root)
		buttonbox.pack()
		
		btnaddurl = Button(buttonbox, text="加入連結")
		btnaddurl.pack(side="left")
		self.btn_addurl = btnaddurl
		
		btnstart = Button(buttonbox, text="開始下載")
		btnstart.pack(side="left")
		self.btn_start = btnstart
		
		btnstop = Button(buttonbox,text="停止下載")
		btnstop.pack(side="left")
		self.btn_stop = btnstop
			
		btnclean = Button(buttonbox, text="移除已完成")
		btnclean.pack(side="left")
		self.btn_clean = btnclean
		
		btnconfig = Button(buttonbox, text="重載設定檔")
		btnconfig.pack(side="left")
		self.btn_config = btnconfig
		
		# notebook
		self.notebook = Notebook(self.root)
		self.notebook.pack(expand=True, fill="both")
		
		# download manager
		frame = Frame(self.notebook)
		self.notebook.add(frame, text="任務列表")
		
		# mission list scrollbar		
		self.view_scrbar = Scrollbar(frame)
		self.view_scrbar.pack(side="right", fill="y")
		
		# mission list
		tv = Treeview(
			frame,
			columns=("name","host","state"),
			yscrollcommand=self.view_scrbar.set
		)
		tv.heading("#0", text="#")
		tv.heading("name", text="任務")
		tv.heading("host", text="主機")
		tv.heading("state", text="狀態")
		tv.column("#0", width="25")
		tv.column("host", width="50", anchor="center")
		tv.column("state", width="70", anchor="center")
		tv.pack(expand=True, fill="both")
		self.tv_view = tv
		
		self.view_scrbar.config(command=tv.yview)
		
		# mission context menu
		self.view_menu = Menu(tv, tearoff=False)
		
		# library
		frame = Frame(self.notebook)
		self.notebook.add(frame, text="圖書館")
		
		# library buttons
		btnBar = Frame(frame)
		btnBar.pack()
		
		self.btn_update = Button(btnBar, text="檢查更新")
		self.btn_update.pack(side="left")
		
		self.btn_download_update = Button(btnBar, text="下載更新")
		self.btn_download_update.pack(side="left")
		
		# library treeview scrollbar container
		frame_lib = Frame(frame)
		frame_lib.pack(expand=True, fill="both")
		
		# scrollbar
		self.lib_scrbar = Scrollbar(frame_lib)
		self.lib_scrbar.pack(side="right", fill="y")
	
		# library treeview
		tv = Treeview(
			frame_lib, 
			columns=("name","host","state"), 
			yscrollcommand=self.lib_scrbar.set
		)
		tv.heading("#0", text="#")
		tv.heading("name", text="任務")
		tv.heading("host", text="主機")
		tv.heading("state", text="狀態")
		tv.column("#0", width="25")
		tv.column("host", width="50", anchor="center")
		tv.column("state", width="70", anchor="center")
		tv.pack(side="left", expand=True, fill="both")
		self.tv_library = tv
		
		self.lib_scrbar.config(command=self.tv_library.yview)
		
		# library context menu
		self.library_menu = Menu(self.tv_library, tearoff=False)
		
		# domain list
		frame = Frame(self.notebook)
		self.notebook.add(frame, text="支援的網域")
		
		# domains scrollbar
		scrollbar = Scrollbar(frame)
		scrollbar.pack(side="right", fill="y")
		
		# domains
		text = Text(frame, height=10, yscrollcommand=scrollbar.set)
		text.insert("insert", "\n".join(mods.list_domain()))
		text.pack(side="left", fill="y")
		
		scrollbar.config(command=text.yview)
		
		# status bar
		statusbar = Label(self.root, text="Comic Crawler", anchor="e")
		statusbar.pack(anchor="e")
		self.statusbar = statusbar
		
	def tkloop(self):
		"""get message from comiccrawler.messageBucket"""
		
		self.cleanup()
		self.root.after(100, self.tkloop)
		
	def remove(self, pool_name, *missions):
		"""Wrap mission_manager.remove"""
		for mission in missions:
			if mission.state in ("DOWNLOADING", "ANALYZING"):
				messagebox.showerror("Comic Crawler", "刪除任務失敗！任務使用中")
		self.downloader.mission_manager.remove(pool_name, *missions)

	def bindevent(self):
		"""Bind events"""
		
		# something about entry
		def trieveclipboard(event):
			# Do nothing if there is something in the entry
			if self.entry_url.get():
				return
				
			try:
				url = self.root.clipboard_get(type="STRING")
			except Exception:
				return
			
			if mods.get_module(url) and url != self.pre_url:
				self.entry_url.insert(0, url)
				self.entry_url.selection_range(0, "end")
				self.entry_url.focus_set()
		self.root.bind("<FocusIn>", trieveclipboard)	
		
		def entrykeypress(event):
			addurl()
		self.entry_url.bind("<Return>", entrykeypress)
		
		def ask_delete_mission(url):
			return messagebox.askyesno(
				"Comic Crawler",
				"任務重覆，要刪除先前任務嗎？",
				default="no"
			)
		
		# interface for download manager
		def addurl():
			url = self.entry_url.get()
			
			try:
				mission = self.downloader.mission_manager.get_by_url(url, "view")
			except KeyError:
				pass
			else:
				if not ask_delete_mission(url):
					return
				self.remove("view", mission)				
				
			self.downloader.add_url(url)
			
			self.entry_url.delete(0, "end")
			self.pre_url = url
		self.btn_addurl["command"] = addurl
		
		def startdownload():
			self.downloader.start_download()
		self.btn_start["command"] = startdownload
		
		def stopdownload():
			self.downloader.stop_download()
		self.btn_stop["command"] = stopdownload
		
		def cleanfinished():
			self.downloader.mission_manager.clean_finished()
		self.btn_clean["command"] = cleanfinished
		
		def reloadconfig():
			self.downloader.reload_config()
			safeprint("設定檔重載成功！")
		self.btn_config["command"] = reloadconfig
		
		def create_menu_set(name):
			"""Create a set of menu"""
			menu = getattr(self, name + "_menu")
			tv = getattr(self, "tv_" + name)
			cid_index = getattr(self, "cid_" + name)
			
			# bind menu helper			
			def bind_menu(label):
				def bind_menu_inner(func):
					menu.add_command(label=label, command=func)
					return func
				return bind_menu_inner
			
			# add commands...
			@bind_menu("刪除")
			def tvdelete():
				if messagebox.askyesno("Comic Crawler", "確定刪除？"):
					selected = tv.selection()
					self.remove(name, *[cid_index[cid] for cid in selected])
			
			@bind_menu("移至頂部")
			def tvlift():
				selected = tv.selection()
				self.downloader.mission_manager.lift(name, *[cid_index[cid] for cid in selected])
				
			@bind_menu("移至底部")
			def tvdrop():
				selected = tv.selection()
				self.downloader.mission_manager.drop(name, *[cid_index[cid] for cid in selected])
			
			@bind_menu("改名")
			def tvchangetitle():
				selected = tv.selection()
				mission = cid_index[selected[0]]
				select_title(self.root, mission)
			
			@bind_menu("重新選擇集數")
			def tvReselectEP():
				s = tv.selection()
				missions = [ cid_index[i] for i in s ]
				for mission in missions:
					reselect_episodes(self.root, mission)
			
			@bind_menu("開啟資料夾")
			def tvOpen():
				s = tv.selection()
				missions = [ cid_index[i] for i in s ]
				savepath = config.get("savepath")
				for mission in missions:
					folder = os.path.join(savepath, safefilepath(mission.title))
					os.startfile(os.path.expanduser(folder))

			@bind_menu("開啟網頁")
			def tvOpenBrowser():
				s = tv.selection()
				missions = [ cid_index[i] for i in s ]
				for mission in missions:
					webbrowser.open(mission.url)
					
			if name == "view":
				@bind_menu("加入圖書館")
				def tvAddToLib():
					s = tv.selection()
					missions = [ cid_index[i] for i in s ]
					titles = [ m.title for m in missions ]
					self.downloader.mission_manager.add("library", *missions)
					safeprint("已加入圖書館︰{}".format(", ".join(titles)))
			
			# menu call
			def tvmenucall(event):
				menu.post(event.x_root, event.y_root)
			tv.bind("<Button-3>", tvmenucall)
			
		create_menu_set("view")
		
		# interface for library
		def libCheckUpdate():
			self.downloader.start_check_update()
		self.btn_update["command"] = libCheckUpdate
		
		def libDownloadUpdate():
			self.downloader.add_mission_update()
			self.downloadManager.start_download()
			self.notebook.select(0)
		self.btn_download_update["command"] = libDownloadUpdate
		
		# interface for library menu
		create_menu_set("library")
		
		def is_running(thread):
			return thread and thread.is_running()
		
		# close window event
		def beforequit():
			if is_running(self.downloader.download_thread):
				if not messagebox.askokcancel(
						"Comic Crawler",
						"任務下載中，確定結束？"):
					return
			self.downloader.stop_download()
			self.root.destroy()
		self.root.protocol("WM_DELETE_WINDOW", beforequit)
		
	def sp_callback(self, text):
		self.message("LOG_MESSAGE", text)
		
	def tv_refresh(self, pool_name):
		"""refresh treeview"""
		
		# cleanup
		tv = getattr(self, "tv_" + pool_name)
		cid_index = getattr(self, "cid_" + pool_name)
		ids = tv.get_children()
		tv.delete(*ids)
		cid_index.clear()
		
		missions = getattr(self.downloader.mission_manager, pool_name).values()
		for mission in missions:
			cid = tv.insert(
				"", 
				"end",
				values=(mission.title, mission.module.name, STATE[mission.state])
			)
			cid_index[cid] = mission
					
def reselect_episodes(parent, mission):
	"""Reselect episode"""
	if select_episodes(parent, mission):
		mission.set("state", "ANALYZED")
		
def select_title(parent, mission):
	"""change mission title dialog"""
	
	w = Dialog(parent)
	
	entry = Entry(w.body)
	entry.insert(0, mission.title)
	entry.selection_range(0, "end")
	entry.pack()
	
	entry.focus_set()
	
	def apply():
		title = entry.get()
		mission.set("title", title)
		
	w.apply = apply
	
	ret = w.wait()
	return ret
	
def select_episodes(parent, mission):
	"""select episode dialog"""
	
	w = Dialog(parent)
	
	xscrollbar = Scrollbar(w.body, orient="horizontal")
	canvas = Canvas(w.body, xscrollcommand=xscrollbar.set, highlightthickness="0")
	inner = Frame(canvas)
	
	# list of checkbutton
	vs = []
	i = 0
	
	# make checkbutton into inner frame
	for ep in mission.episodes:
		ck = Checkbutton(inner, text=ep.title)
		ck.state(("!alternate",))
		if not ep.skip:
			ck.state(("selected",))
		ck.grid(column=i // 20, row=i % 20, sticky="w")
		vs.append((ck, ep))
		i += 1
		
	def colsel(gck, c):
		def _():
			for i in range(c*20, (c+1)*20):
				if i >= len(vs):
					break
				ck, ep = vs[i]
				if gck.instate(("selected", )):
					ck.state(("selected", ))
				else:
					ck.state(("!selected", ))
		return _
		
	from math import ceil
	for i in range(ceil(len(mission.episodes) / 20)):
		ck = Checkbutton(inner)
		ck.state(("!alternate", "selected"))
		ck.grid(column=i, row=20, sticky="w")
		ck.config(command=colsel(ck, i))
		
	# caculates frame size after inner frame configured and resize canvas
	def t(event):
		canvas.config(scrollregion=inner.bbox("ALL"), 
				height=inner.bbox("ALL")[3], 
				width=inner.bbox("ALL")[2])
		inner.unbind("<Configure>")
	inner.bind("<Configure>", t)
	
	# caculates canvas's size then deside wether to show scrollbar
	def t(event):
		if canvas.winfo_width() >= canvas.winfo_reqwidth():
			xscrollbar.pack_forget()
		canvas.unbind("<Configure>")
	canvas.bind("<Configure>", t)
	
	# draw innerframe on canvas then show
	canvas.create_window((0,0),window=inner, anchor='nw')
	canvas.pack()
	
	# link scrollbar to canvas then show
	xscrollbar.config(command=canvas.xview)
	xscrollbar.pack(fill="x")
	
	def apply():
		for v in vs:
			ck, ep = v
			ep.skip = not ck.instate(("selected",))
		w.result = len([ i for i in mission.episodes if not i.skip ])
	w.apply = apply
	
	def toggle():
		for v in vs:
			ck, ep = v
			if ck.instate(("selected", )):
				ck.state(("!selected", ))
			else:
				ck.state(("selected", ))
	for i in w.buttonbox.winfo_children():
		i.destroy()
	Button(w.buttonbox, text="反相", command=toggle).pack(side="left")
	Button(w.buttonbox, text="確定", command=w.ok, default=ACTIVE).pack(side="left")
	Button(w.buttonbox, text="取消", command=w.cancel).pack(side="left")
	
	return w.wait()

