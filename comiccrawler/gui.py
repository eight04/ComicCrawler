#! python3

"""Comic Crawler GUI."""

from tkinter import *
from tkinter.ttk import *
from functools import partial
from worker import current
from time import time

import sys, os, webbrowser, worker, re
import tkinter.messagebox as messagebox

from .mods import list_domain, get_module, load_config
from .config import setting
from .safeprint import print, printer
from .core import safefilepath, create_mission
from .error import ModuleError
from .download_manager import download_manager
from .mission_manager import mission_manager
from .channel import download_ch, mission_ch, message_ch

# Translate state code to readible text.
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

def safe_tk(text):
	"""Encode U+FFFF+ characters. Tkinter doesn't allow to display these character. See http://stackoverflow.com/questions/23530080/how-to-print-non-bmp-unicode-characters-in-tkinter-e-g"""

	return re.sub(r"[^\u0000-\uFFFF]", "_", text)

class DialogProvider:
	"""Create dialog elements."""

	def __init__(self, dialog):
		"""Construct. Inject dialog instance."""
		self.dialog = dialog

	def create_body(self, body):
		"""Override me."""
		pass

	def create_btn_bar(self, btn_bar):
		"""Override me."""
		Button(btn_bar, text="確定", command=self.dialog.ok, default=ACTIVE).pack(side="left")
		Button(btn_bar, text="取消", command=self.dialog.cancel).pack(side="left")

	def apply(self):
		"""Override me."""
		return True

class Dialog(Toplevel):
	"""Create dialog."""

	def __init__(self, parent, title="Dialog", cls=DialogProvider):
		"""Construct."""

		super().__init__(parent)

		self.parent = parent
		self.result = None
		self.provider = cls(self)

		# title
		self.title(safe_tk(title))

		# body
		self.body = Frame(self)
		self.provider.create_body(self.body)
		self.body.pack()

		# button bar
		self.btn_bar = Frame(self)
		self.provider.create_btn_bar(self.btn_bar)
		self.btn_bar.pack()

		# bind event
		self.bind("<Return>", self.ok)
		self.bind("<Escape>", self.cancel)

		# show dialog and disable parent
		self.grab_set()
		self.protocol("WM_DELETE_WINDOW", self.cancel)
		self.focus_set()

	def ok(self, event=None):
		"""Apply and destroy dialog."""
		self.withdraw()
		self.update_idletasks()
		self.result = self.provider.apply()
		self.parent.focus_set()
		self.destroy()

	def cancel(self, event=None):
		"""Destroy dialog."""
		self.parent.focus_set()
		self.destroy()

	def wait(self):
		"""Wait the dialog to close."""
		self.wait_window(self)
		return self.result

class MainWindow:
	"""Create main window GUI."""
	def __init__(self):
		"""Construct."""
		
		self.thread = current()
		
		self.cid_view = {}
		self.cid_library = {}
		self.pre_url = None

		self.create_view()
		
		self.bindevent()
		
		self.register_listeners()
		
		printer.add_listener(self.sp_callback)

		if (setting.getboolean("libraryautocheck") and
			time() - setting.getfloat("lastcheckupdate", 0) > 24 * 60 * 60):
			download_manager.start_check_update()
		
		self.save()
		self.update()
		self.root.mainloop()
		
	def update(self):
		"""Cleanup message every 100 milliseconds."""
		self.thread.update()
		self.root.after(100, self.update)
		
	def save(self):
		"""Save mission periodly"""
		mission_manager.save()
		self.root.after(setting.getint("autosave", 5) * 60 * 1000, self.save)

	def get_cid(self, cid_index, mission):
		"""Get matched cid from cid index."""
		for cid, mission2 in cid_index.items():
			if mission2 is mission:
				return cid

	def update_mission_info(self, tv, cid, mission):
		"""Update mission info on treeview."""
		tv.set(cid, "state", STATE[mission.state])
		tv.set(cid, "name", safe_tk(mission.title))

	def register_listeners(self):
		"""Add listeners."""
		
		mission_ch.sub(self.thread)
		download_ch.sub(self.thread)
		message_ch.sub(self.thread)
		
		@self.thread.listen("LOG_MESSAGE")
		def _(event):
			text = event.data.splitlines()[0]
			self.statusbar["text"] = safe_tk(text)

		@self.thread.listen("MISSION_PROPERTY_CHANGED")
		def _(event):
			cid = self.get_cid(self.cid_view, event.data)
			if cid is not None:
				self.update_mission_info(self.tv_view, cid, event.data)

			cid = self.get_cid(self.cid_library, event.data)
			if cid is not None:
				self.update_mission_info(self.tv_library, cid, event.data)

		@self.thread.listen("MISSION_LIST_REARRANGED")
		def _(event):
			if event.data == self.downloader.mission_manager.view:
				self.tv_refresh("view")
			if event.data == self.downloader.mission_manager.library:
				self.tv_refresh("library")

		@self.thread.listen("MISSION_ADDED")
		def _(event):
			mission = event.data
			if len(mission.episodes) == 1:
				return
				
			if not select_episodes(self.root, mission):
				mission_manager.remove("view", mission)

		@self.thread.listen("ANALYZE_FAILED")
		def _(event):
			error, mission = event.data
			messagebox.showerror(
				mission.module.name,
				"解析錯誤！\n{}".format(error)
			)

		@self.thread.listen("MISSION_POOL_LOAD_FAILED")
		def _(event):
			messagebox.showerror(
				"Comic Crawler",
				"讀取存檔失敗！\n{}".format(event.data)
			)

		@self.thread.listen("DOWNLOAD_INVALID")
		def _(event):
			err, mission = event.data
			messagebox.showerror(mission.module.name, err)

		@self.thread.listen("ANALYZE_INVALID")
		def _(event):
			err, mission = event.data
			messagebox.showerror(mission.module.name, err)

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
		text.insert("insert", "\n".join(list_domain()))
		text.pack(side="left", fill="y")

		scrollbar.config(command=text.yview)

		# status bar
		statusbar = Label(self.root, text="Comic Crawler", anchor="e")
		statusbar.pack(anchor="e")
		self.statusbar = statusbar

	def remove(self, pool_name, *missions):
		"""Wrap mission_manager.remove."""
		for mission in missions:
			if mission.state in ("DOWNLOADING", "ANALYZING"):
				messagebox.showerror("Comic Crawler", "刪除任務失敗！任務使用中")
		mission_manager.remove(pool_name, *missions)

	def bindevent(self):
		"""Bind events."""
		def trieveclipboard(event):
			# Do nothing if there is something in the entry
			if self.entry_url.get():
				return

			try:
				url = self.root.clipboard_get(type="STRING")
			except Exception:
				return

			if get_module(url) and url != self.pre_url:
				self.entry_url.insert(0, url)
				self.entry_url.selection_range(0, "end")
				self.entry_url.focus_set()
		self.root.bind("<FocusIn>", trieveclipboard)

		def entrykeypress(event):
			addurl()
		self.entry_url.bind("<Return>", entrykeypress)

		def ask_analyze_update(mission):
			return messagebox.askyesno(
				"Comic Crawler",
				safe_tk(mission.title) + "\n\n任務已存在，要檢查更新嗎？",
				default="yes"
			)

		# interface for download manager
		def addurl():
			url = self.entry_url.get()
			self.entry_url.delete(0, "end")

			try:
				mission = mission_manager.get_by_url(url)
			except KeyError:
				pass
			else:
				self.pre_url = url
				if ask_analyze_update(mission):
					download_manager.start_analyze(mission)
				return
					
			try:
				mission = create_mission(url)
			except ModuleError:
				messagebox.showerror(
					"Comic Crawler",
					"建立任務失敗！不支援的網址！"
				)
			else:
				self.pre_url = url
				download_manager.start_analyze(mission)

		self.btn_addurl["command"] = addurl

		def startdownload():
			download_manager.start_download()
		self.btn_start["command"] = startdownload

		def stopdownload():
			download_manager.stop_download()
		self.btn_stop["command"] = stopdownload

		def cleanfinished():
			# mission_manager.clean_finished()
			missions = mission_manager.get_by_state("view", ("FINISHED",), all=True)
			mission_manager.remove("view", *missions)
		self.btn_clean["command"] = cleanfinished

		def reloadconfig():
			config.load()
			load_config()
			print("設定檔重載成功！")
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
				mission_manager.lift(name, *[cid_index[cid] for cid in selected])

			@bind_menu("移至底部")
			def tvdrop():
				selected = tv.selection()
				mission_manager.drop(name, *[cid_index[cid] for cid in selected])

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
				savepath = setting["savepath"]
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
					mission_manager.add("library", *missions)
					print("已加入圖書館︰{}".format(", ".join(titles)))

			# menu call
			def tvmenucall(event):
				menu.post(event.x_root, event.y_root)
			tv.bind("<Button-3>", tvmenucall)

		create_menu_set("view")

		# library buttons
		def libCheckUpdate():
			download_manager.start_check_update()
		self.btn_update["command"] = libCheckUpdate

		def libDownloadUpdate():
			missions = mission_manager.get_by_state("library", ("UPDATE",), all=True)
			if not missions:
				messagebox.showerror("Comic Crawler", "沒有新更新的任務")
				return
			mission_manager.add("view", *missions)
			download_manager.start_download()
			self.notebook.select(0)
		self.btn_download_update["command"] = libDownloadUpdate

		# library menu
		create_menu_set("library")

		# close window event
		def beforequit():
			if download_manager.is_downloading():
				if not messagebox.askokcancel(
						"Comic Crawler",
						"任務下載中，確定結束？"):
					return
					
			# going to quit
			printer.remove_listener(self.sp_callback)		
		
			self.root.destroy()
			
			download_manager.stop_download()
			download_manager.stop_analyze()
			download_manager.stop_check_update()
			
			mission_manager.save()
			
			config.save()
			
		self.root.protocol("WM_DELETE_WINDOW", beforequit)

	def sp_callback(self, text):
		"""Transport text to LOG_MESSAGE event."""
		message_ch.pub("LOG_MESSAGE", text)

	def tv_refresh(self, pool_name):
		"""Refresh treeview."""

		# cleanup
		tv = getattr(self, "tv_" + pool_name)
		cid_index = getattr(self, "cid_" + pool_name)
		ids = tv.get_children()
		tv.delete(*ids)
		cid_index.clear()

		missions = getattr(mission_manager, pool_name).values()
		for mission in missions:
			cid = tv.insert(
				"",
				"end",
				values=(safe_tk(mission.title), mission.module.name, STATE[mission.state])
			)
			cid_index[cid] = mission

def reselect_episodes(parent, mission):
	"""Reselect episode"""
	if select_episodes(parent, mission):
		mission.state = "ANALYZED"

def select_title(parent, mission):
	"""Create dialog to change mission title."""

	class Provider(DialogProvider):
		def create_body(self, body):
			entry = Entry(body)
			entry.insert(0, safe_tk(mission.title))
			entry.selection_range(0, "end")
			entry.pack()
			entry.focus_set()
			self.entry = entry

		def apply(self):
			title = self.entry.get()
			mission.title = title

	return Dialog(parent, title="重命名", cls=Provider).wait()

def select_episodes(parent, mission):
	"""Create dialog to select episodes."""

	class Provider(DialogProvider):
		def create_body(self, body):
			xscrollbar = Scrollbar(body, orient="horizontal")
			canvas = Canvas(
				body,
				xscrollcommand=xscrollbar.set,
				highlightthickness="0"
			)

			# split to each page
			pages = [mission.episodes[i:i + 20] for i in range(0, len(mission.episodes), 20)]
			# split to each window
			windows = [pages[i:i + 10] for i in range(0, len(pages), 10)]

			self.ck_holder = ck_holder = {}

			def set_page(ck, page):
				def callback():
					if ck.instate(("selected",)):
						value = ("selected", )
					else:
						value = ("!selected", )

					for ep in page:
						ck_holder[ep].state(value)
				return callback

			left = 0
			for window in windows:
				inner = Frame(canvas)
				for p_i, page in enumerate(window):
					for e_i, ep in enumerate(page):
						ck = Checkbutton(inner, text=safe_tk(ep.title))
						ck.state(("!alternate",))
						if not ep.skip:
							ck.state(("selected",))
						ck.grid(column=p_i, row=e_i, sticky="w")
						ck_holder[ep] = ck
					ck = Checkbutton(inner)
					ck.state(("!alternate", "selected"))
					ck.grid(column=p_i, row=e_i + 1, sticky="w")
					ck.config(command=set_page(ck, page))
				canvas.create_window((left, 0), window=inner, anchor="nw")
				inner.update_idletasks()
				left += inner.winfo_reqwidth()

			# Resize canvas
			canvas.update_idletasks()
			cord = canvas.bbox("all")
			canvas.config(
				scrollregion=cord,
				height=cord[3],
				width=cord[2]
			)

			# caculates canvas's size then deside wether to show scrollbar
			def decide_scrollbar(event):
				if canvas.winfo_width() >= canvas.winfo_reqwidth():
					xscrollbar.pack_forget()
					canvas.unbind("<Configure>")
			canvas.bind("<Configure>", decide_scrollbar)

			# draw innerframe on canvas then show
			canvas.pack()

			# link scrollbar to canvas then show
			xscrollbar.config(command=canvas.xview)
			xscrollbar.pack(fill="x")

		def create_btn_bar(self, btn_bar):
			Button(btn_bar, text="反相", command=self.toggle).pack(side="left")
			super().create_btn_bar(btn_bar)

		def apply(self):
			for ep, ck in self.ck_holder.items():
				ep.skip = not ck.instate(("selected",))
			return len([ i for i in mission.episodes if not i.skip ])

		def toggle(self):
			for ep, ck in self.ck_holder.items():
				if ck.instate(("selected", )):
					ck.state(("!selected", ))
				else:
					ck.state(("selected", ))

	return Dialog(parent, title="選擇集數", cls=Provider).wait()
