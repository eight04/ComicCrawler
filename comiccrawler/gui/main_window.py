#! python3

from contextlib import contextmanager
import os
import webbrowser
import sys
from time import time, strftime, localtime

import tkinter as tk
from tkinter import ttk, font, messagebox

import desktop
import worker

from ..mods import list_domain, get_module, load_config
from ..config import setting, config
from ..safeprint import print, printer
from ..mission import create_mission
from ..error import ModuleError
from ..profile import get as profile
from ..util import safefilepath, MIN

from ..download_manager import download_manager
from ..mission_manager import mission_manager
from ..channel import download_ch, mission_ch, message_ch
from ..episode_loader import load_episodes, edit_mission_id

from .table import Table
from .dialog import Dialog
from .core import get_scale, safe_tk, STATE
from .select_episodes import select_episodes

def reselect_episodes(root, mission):
	with load_episodes(mission):
		if select_episodes(root, mission):
			mission.state = "ANALYZED"

def draw_last_update(t):
	if not t:
		return "無"
	return strftime("%Y/%m/%d", localtime(t))

def create_mission_table(parent):
	return Table(
		parent,
		columns = [{
			"id": "#0",
			"text": "#",
			"width": 25
		}, {
			"id": "name",
			"text": "任務"
		}, {
			"id": "host",
			"text": "主機",
			"width": 50,
			"anchor": "center"
		}, {
			"id": "state",
			"text": "狀態",
			"width": 70,
			"anchor": "center"
		}, {
			"id": "last_update",
			"text": "更新",
			"width": 70,
			"anchor": "center",
			"sort": "DESC"
		}]
	)
	
def select_title(parent, mission):
	"""Create dialog to change mission title."""
	class _Dialog(Dialog):
		def create_body(self):
			entry = ttk.Entry(self.body)
			entry.insert(0, safe_tk(mission.title))
			entry.selection_range(0, "end")
			entry.pack()
			entry.focus_set()
			self.entry = entry

		def apply(self):
			return self.entry.get()
			
	new_title = _Dialog(parent, title="重命名").wait()
	if not new_title:
		return
	with edit_mission_id(mission):
		mission.title = new_title

class TkinterLoop:
	def __init__(self, root, do_stuff, delay=100):
		self.root = root
		self.delay = delay
		self.do_stuff = do_stuff
		
	def start(self):
		self.root.after_id = self.root.after(self.delay, self.after)
		self.root.mainloop()
		
	def after(self):
		self.root.after_id = self.root.after(self.delay, self.after)
		self.do_stuff()
		
	@contextmanager
	def pause(self):
		self.root.after_cancel(self.root.after_id)
		try:
			yield
		finally:
			self.root.after_id = self.root.after(self.delay, self.after)
			
class ViewMixin:
	"""Create main window view"""
	def create_view(self):
		"""Draw the window."""
		
		# root
		self.root = tk.Tk()
		self.root.title("Comic Crawler")
		
		# setup theme on linux
		if sys.platform.startswith("linux"):
			try:
				ttk.Style().theme_use("clam")
			except tk.TclError:
				pass
		
		# adjust scale, dimension
		scale = max(get_scale(self.root), 1.0)

		self.root.geometry("{w}x{h}".format(
			w=int(500 * scale),
			h=int(400 * scale)
		))
		
		if scale != 1:
			old_scale = self.root.tk.call('tk', 'scaling')
			self.root.tk.call("tk", "scaling", old_scale * scale)
			
		# Use pt for builtin fonts
		for name in ("TkDefaultFont", "TkTextFont", "TkHeadingFont",
				"TkMenuFont", "TkFixedFont", "TkTooltipFont", "TkCaptionFont",
				"TkSmallCaptionFont", "TkIconFont"):
			f = font.nametofont(name)
			size = f.config()["size"]
			if size < 0:
				size = int(-size / 96 * 72)
				f.config(size=size)

		# Treeview doesn't scale its rowheight
		ttk.Style().configure("Treeview", rowheight=int(20 * scale))
		
		# url label
		tk.Label(self.root,text="輸入連結︰").pack(anchor="w")

		# url entry
		entry_url = ttk.Entry(self.root)
		entry_url.pack(fill="x")
		self.entry_url = entry_url

		# bunch of buttons
		self.create_btn_bar()

		# notebook
		self.notebook = ttk.Notebook(self.root)
		self.notebook.pack(expand=True, fill="both")

		# download manager
		frame = ttk.Frame(self.notebook)
		self.notebook.add(frame, text="任務列表")
		
		# mission table
		self.view_table = create_mission_table(frame)

		# library
		frame = ttk.Frame(self.notebook)
		self.notebook.add(frame, text="圖書館")

		# library buttons
		btn_bar = ttk.Frame(frame)
		btn_bar.pack()

		self.btn_update = ttk.Button(btn_bar, text="檢查更新")
		self.btn_update.pack(side="left")

		self.btn_download_update = ttk.Button(btn_bar, text="下載更新")
		self.btn_download_update.pack(side="left")

		# library treeview scrollbar container
		frame_lib = ttk.Frame(frame)
		frame_lib.pack(expand=True, fill="both")
		
		# library table
		self.library_table = create_mission_table(frame_lib)

		# domain list
		frame = ttk.Frame(self.notebook)
		self.notebook.add(frame, text="支援的網域")
		
		table = Table(frame, columns = [{
			"id": "host",
			"text": "域名"
		}, {
			"id": "mod",
			"text": "模組",
			"anchor": "center"
		}], tv_opt={"show": "headings"})
		
		for domain, module in list_domain(True):
			table.add({
				"host": domain,
				"mod": module.name
			})
			
		# batch analyzer
		frame = ttk.Frame(self.notebook)
		self.notebook.add(frame, text="批次加入")
		
		btn_bar = ttk.Frame(frame)
		btn_bar.pack()
		
		self.btn_batch_analyze = ttk.Button(btn_bar, text="開始分析")
		self.btn_batch_analyze.pack(side="left")
		
		self.btn_batch_analyze_stop = ttk.Button(btn_bar, text="停止分析")
		self.btn_batch_analyze_stop.pack(side="left")
		
		self.text_batch_analyze = create_scrollable_text(frame)
			
		# status bar
		statusbar = ttk.Label(self.root, text="Comic Crawler", anchor="e")
		statusbar.pack(anchor="e")
		self.statusbar = statusbar
		
	def create_btn_bar(self):
		"""Draw the button bar"""
		buttonbox = ttk.Frame(self.root)
		buttonbox.pack()

		btnaddurl = ttk.Button(buttonbox, text="加入連結")
		btnaddurl.pack(side="left")
		self.btn_addurl = btnaddurl

		btnstart = ttk.Button(buttonbox, text="開始下載")
		btnstart.pack(side="left")
		self.btn_start = btnstart

		btnstop = ttk.Button(buttonbox, text="停止下載")
		btnstop.pack(side="left")
		self.btn_stop = btnstop

		btnclean = ttk.Button(buttonbox, text="移除已完成")
		btnclean.pack(side="left")
		self.btn_clean = btnclean

		btnconfig = ttk.Button(buttonbox, text="重載設定檔")
		btnconfig.pack(side="left")
		self.btn_config = btnconfig
	
class EventMixin:
	"""Bind main window events"""
	def bind_event(self):
		"""Bind events."""
		pre_url = None
		
		def trieveclipboard(_event):
			nonlocal pre_url
			# Do nothing if there is something in the entry
			if self.entry_url.get():
				return

			try:
				url = self.root.clipboard_get(type="STRING")
			except tk.TclError:
				return
				
			if "\n" in url:
				return

			if get_module(url) and url != pre_url:
				pre_url = url
				self.entry_url.insert(0, url)
				self.entry_url.selection_range(0, "end")
				self.entry_url.focus_set()
		self.root.bind("<FocusIn>", trieveclipboard)

		def entrykeypress(_event):
			addurl()
		self.entry_url.bind("<Return>", entrykeypress)

		# interface for download manager
		def addurl():
			url = self.entry_url.get()
			self.entry_url.delete(0, "end")
			self.add_url(url)
		self.btn_addurl["command"] = addurl

		def startdownload():
			download_manager.start_download()
		self.btn_start["command"] = startdownload

		def stopdownload():
			download_manager.stop_download()
			print("停止下載")
		self.btn_stop["command"] = stopdownload

		def cleanfinished():
			# mission_manager.clean_finished()
			missions = mission_manager.get_all("view", lambda m: m.state == "FINISHED")
			if not missions:
				return
			mission_manager.remove("view", *missions)
			print("移除 " + ", ".join(mission.title for mission in missions))
		self.btn_clean["command"] = cleanfinished

		def reloadconfig():
			config.load()
			load_config()
			print("設定檔重載成功！")
		self.btn_config["command"] = reloadconfig

		def create_menu_set(name, table):
			"""Create a set of menu"""
			menu = tk.Menu(table.tv, tearoff=False)

			# bind menu helper
			def bind_menu(label):
				def bind_menu_inner(func):
					menu.add_command(label=label, command=func)
					return func
				return bind_menu_inner

			# add commands...
			@bind_menu("刪除")
			def _():
				if self.messagebox("yesno", "Comic Crawler", "確定刪除？"):
					self.remove(name, *table.selected())
					
			if name == "view":
				@bind_menu("刪除（包括圖書館）")
				def _():
					if self.messagebox("yesno", "Comic Crawler", "確定刪除？"):
						selected = table.selected()
						self.remove("view", *selected)
						self.remove("library", *selected)

			@bind_menu("移至頂部")
			def _():
				mission_manager.lift(name, *table.selected())

			@bind_menu("移至底部")
			def _():
				mission_manager.drop(name, *table.selected())

			@bind_menu("改名")
			def _():
				selected = table.selected()
				if not selected:
					return
				mission = selected[0]
				select_title(self.root, mission)

			@bind_menu("重新選擇集數")
			def _():
				for mission in table.selected():
					reselect_episodes(self.root, mission)

			@bind_menu("開啟資料夾")
			def start_explorer(event=None):
				if event:
					mission = table.identify_row(event.y)
					if not mission:
						# click on header
						return
					missions = [mission]
				else:
					missions = table.selected()
					
				for mission in missions:
					savepath = profile(mission.module.config["savepath"])
					folder = os.path.join(savepath, safefilepath(mission.title))
					folder = os.path.expanduser(folder)
					if not os.path.isdir(folder):
						os.makedirs(folder)
					desktop.open(folder)

			@bind_menu("開啟網頁")
			def _():
				for mission in table.selected():
					webbrowser.open(mission.url)

			if name == "view":
				@bind_menu("加入圖書館")
				def _():
					missions = table.selected()
					titles = [ m.title for m in missions ]
					mission_manager.add("library", *missions)
					print("已加入圖書館︰{}".format(", ".join(titles)))
					
			if name == "library":
				@bind_menu("檢查更新")
				def _():
					missions = table.selected()
					download_manager.start_check_update(missions)
					
			# menu call
			def tvmenucall(event):
				menu.tk_popup(event.x_root, event.y_root)
			table.tv.bind("<Button-3>", tvmenucall)

			# dubleclick to start explorer
			table.tv.bind("<Double-Button-1>", start_explorer)
			
			# sort
			def on_sort(table):
				def key_func(m):
					if table.sort_on == "host":
						return m.module.name
					if table.sort_on == "name":
						return m.title
					if table.sort_on == "state":
						return m.state
					if table.sort_on == "last_update":
						return m.last_update or MIN
				mission_manager.sort(name, key_func, reverse=table.sort_mode == "DESC")
			table.on("sort", on_sort)

		create_menu_set("view", self.view_table)

		# library buttons
		def lib_check_update():
			download_manager.start_check_update()
		self.btn_update["command"] = lib_check_update

		def lib_download_update():
			missions = mission_manager.get_all("library", lambda m: m.state == "UPDATE")
			if not missions:
				self.messagebox("error", "Comic Crawler", "沒有新更新的任務")
				return
			mission_manager.add("view", *missions)
			download_manager.start_download()
			self.notebook.select(0)
		self.btn_download_update["command"] = lib_download_update

		# library menu
		create_menu_set("library", self.library_table)
		
		# batch analyze
		def batch_analyze():
			text = self.text_batch_analyze.get("1.0", "end")
			
			try:
				download_manager.start_batch_analyze(text)
			except Exception as err: # pylint: disable=broad-except
				self.messagebox("error", "Comic Crawler", "Failed to batch: {}".format(err))
				return
					
			self.text_batch_analyze.config(state="disabled")
		self.btn_batch_analyze["command"] = batch_analyze
		
		def batch_analyze_stop():
			download_manager.stop_batch_analyze()
		self.btn_batch_analyze_stop["command"] = batch_analyze_stop

		# close window event
		def beforequit():
			if download_manager.is_downloading():
				if not self.messagebox("okcancel", "Comic Crawler", "任務下載中，確定結束？"):
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

class MainWindow(ViewMixin, EventMixin):
	"""Create main window GUI."""
	def __init__(self):
		"""Construct."""
		self.create_view()
		self.bind_event()
		
		self.thread = worker.current()
		self.loop = TkinterLoop(self.root, worker.update)

		self.pool_index = {
			id(mission_manager.view): self.view_table,
			id(mission_manager.library): self.library_table
		}
		
		self.register_listeners()
		
		printer.add_listener(self.sp_callback)

		if (setting.getboolean("libraryautocheck") and
			time() - setting.getfloat("lastcheckupdate", 0) > setting.getfloat("autocheck_interval") * 60 * 60):
			download_manager.start_check_update()
			
		self.update_table(mission_manager.view)
		self.update_table(mission_manager.library)
		
		self.save()
		self.loop.start()
		
	def messagebox(self, type, *args, **kwargs):
		"""Pause the loop when using messagebox"""
		name = None
		if type in ("okcancel", "yesno", "yesnocancel", "retrycancel"):
			name = "ask" + type
		else:
			name = "show" + type
		func = getattr(messagebox, name)
		with self.loop.pause():
			return func(*args, **kwargs)
			
	def save(self):
		"""Save mission periodly"""
		mission_manager.save()
		self.root.after(int(setting.getfloat("autosave", 5) * 60 * 1000), self.save)

	def update_mission_info(self, table, mission):
		"""Update mission info on treeview."""
		if not table.contains(mission):
			return
		table.update(
			mission,
			name=safe_tk(mission.title),
			state=STATE[mission.state],
			last_update=draw_last_update(mission.last_update)
		)

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
			self.update_mission_info(self.view_table, event.data)
			self.update_mission_info(self.library_table, event.data)

		@self.thread.listen("MISSION_LIST_REARRANGED")
		def _(event):
			self.update_table(event.data)

		@self.thread.listen("MISSION_POOL_LOAD_FAILED")
		def _(event):
			self.messagebox(
				"error",
				"Comic Crawler",
				"讀取存檔失敗！\n{}".format(event.data)
			)

		@self.thread.listen("DOWNLOAD_INVALID")
		def _(event):
			err, mission = event.data
			self.messagebox("error", mission.module.name, err)

		@self.thread.listen("ANALYZE_INVALID")
		def _(event):
			err, mission = event.data
			self.messagebox("error", mission.module.name, err)
			
		@self.thread.listen("LIBRARY_CHECK_UPDATE_FAILED")
		def _(event):
			if hasattr(event.data, "mission"):
				title = event.data.mission.module.name
			else:
				title = "Comic Crawler"
			self.messagebox("error", title, str(event.data))
			
		@self.thread.listen("BATCH_ANALYZE_UPDATE")
		def _(event):
			self.update_batch_text(event.data)
			
		@self.thread.listen("BATCH_ANALYZE_END")
		def _(event):
			err = event.data
			if err and not isinstance(err, worker.WorkerExit):
				self.messagebox("error", "Comic Crawler", "批次加入失敗！{}".format(err))
			self.text_batch_analyze.config(state="normal")
			print("Batch analyze ended")
			
	def update_batch_text(self, missions):
		text = "\n".join(m.url for m in missions)
		self.text_batch_analyze.config(state="normal")
		self.text_batch_analyze.delete("1.0", "end")
		self.text_batch_analyze.insert("1.0", text)
		self.text_batch_analyze.config(state="disabled")
			
	def remove(self, pool_name, *missions):
		"""Wrap mission_manager.remove."""
		for mission in missions:
			if mission.state in ("DOWNLOADING", "ANALYZING"):
				self.messagebox("error", "Comic Crawler", "刪除任務失敗！任務使用中")
		mission_manager.remove(pool_name, *missions)

	def sp_callback(self, text):
		"""Transport text to LOG_MESSAGE event."""
		message_ch.pub("LOG_MESSAGE", text)

	def update_table(self, pool):
		"""Refresh treeview."""
		table = self.pool_index[id(pool)]
		missions = pool.values()
		
		table.clear(exclude=missions)
		
		for mission in missions:
			if not table.contains(mission):
				table.add({
					"name": safe_tk(mission.title),
					"host": mission.module.name,
					"state": STATE[mission.state],
					"last_update": draw_last_update(mission.last_update)
				}, key=mission)
				
		table.rearrange(missions)
		
	def add_analyze(self, mission, on_success=None):
		def on_finished(err):
			if err and not isinstance(err, worker.WorkerExit):
				self.thread.later(
					self.messagebox,
					"error",
					mission.module.name,
					"解析錯誤！\n{}".format(err)
				)
			if not err and on_success:
				on_success()
		download_manager.start_analyze(mission, on_finished=on_finished)
		
	def add_url(self, url):
		try:
			mission = mission_manager.get_by_url(url)
		except KeyError:
			pass
		else:
			conflict_action = mission.module.config.get("mission_conflict_action")
			if conflict_action == "update":
				if self.messagebox(
					"yesno",
					"Comic Crawler",
					safe_tk(mission.title) + "\n\n任務已存在，要檢查更新嗎？",
					default="yes"
				):
					mission.state = 'ANALYZE_INIT'
					self.add_analyze(mission)
			elif conflict_action == "reselect_episodes":
				reselect_episodes(self.root, mission)
			else:
				self.messagebox("error", "Comic Crawler", "任務已存在")
				
			return
		try:
			mission = create_mission(url=url)
		except ModuleError:
			self.messagebox(
				"error",
				"Comic Crawler",
				"建立任務失敗！不支援的網址！"
			)
			return
			
		def on_success():
			if len(mission.episodes) == 1:
				return
				
			if not mission.module.config.getboolean("selectall"):
				for ep in mission.episodes:
					ep.skip = True
					
			# note that on_finished is called in the analyzer thread, we can't
			# call select_episodes directly.
			defer = worker.Defer()
			self.thread.later(select_episodes, self.root, mission, on_closed=defer.resolve)
			if not defer.get():
				mission_manager.remove("view", mission)
				
		self.add_analyze(mission, on_success=on_success)
		
def create_scrollable_text(parent):
	scrbar = ttk.Scrollbar(parent)
	scrbar.pack(side="right", fill="y")
	
	text = tk.Text(parent, height=3, yscrollcommand=scrbar.set)
	text.pack(expand=True, fill="both")
	
	scrbar.config(command=text.yview)

	return text
