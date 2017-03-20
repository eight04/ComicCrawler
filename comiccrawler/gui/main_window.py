#! python3

import os
import webbrowser
import sys
from time import time

import tkinter as tk
from tkinter import ttk, font, messagebox

import desktop
from worker import current

from ..mods import list_domain, get_module, load_config, domain_index
from ..config import setting, config
from ..safeprint import print, printer
from ..core import safefilepath, create_mission
from ..error import ModuleError
from ..profile import get as profile

from ..download_manager import download_manager
from ..mission_manager import (mission_manager, init_episode, uninit_episode,
	edit_mission_id)
from ..channel import download_ch, mission_ch, message_ch

from .table import Table
from .dialog import Dialog
from .core import get_scale, safe_tk, STATE

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

def select_episodes(parent, mission):
	"""Create dialog to select episodes."""
	class _Dialog(Dialog):
		def create_body(self):
			xscrollbar = ttk.Scrollbar(self.body, orient="horizontal")
			canvas = tk.Canvas(
				self.body,
				xscrollcommand=xscrollbar.set,
				highlightthickness="0"
			)

			self.checks = []

			def set_page(check, start, end):
				def callback():
					if check.instate(("selected",)):
						value = ("selected", )
					else:
						value = ("!selected", )

					for i in range(start, end):
						self.checks[i][1].state(value)
				return callback

			window = None
			window_column = 0
			window_left = 0
			for i, ep in enumerate(mission.episodes):
				# create a new window for every 200 items
				if i % 200 == 0:
					if window:
						window.update_idletasks()
						window_left += window.winfo_reqwidth()
						window_column = i // 20
					window = ttk.Frame(canvas)
					canvas.create_window((window_left, 0), window=window,
						anchor="nw")
			
				check = ttk.Checkbutton(window, text=safe_tk(ep.title))
				check.state(("!alternate",))
				if not ep.skip:
					check.state(("selected",))
				check.grid(
					column=(i // 20) - window_column,
					row=i % 20,
					sticky="w"
				)
				self.checks.append((ep, check))
				
				# checkbutton for each column
				if i % 20 == 19 or i == len(mission.episodes) - 1:
					check = ttk.Checkbutton(window)
					check.state(("!alternate", "selected"))
					check.grid(
						column=(i // 20) - window_column,
						row=20,
						sticky="w"
					)
					check.config(command=set_page(check, i - 19, i + 1))
					
			# Resize canvas
			canvas.update_idletasks()
			cord = canvas.bbox("all")
			canvas.config(
				scrollregion=cord,
				height=cord[3],
				width=cord[2]
			)

			# caculates canvas's size then deside whether to show scrollbar
			def decide_scrollbar(_event):
				if canvas.winfo_width() >= canvas.winfo_reqwidth():
					xscrollbar.pack_forget()
					canvas.unbind("<Configure>")
			canvas.bind("<Configure>", decide_scrollbar)

			# draw innerframe on canvas then show
			canvas.pack()

			# link scrollbar to canvas then show
			xscrollbar.config(command=canvas.xview)
			xscrollbar.pack(fill="x")

		def create_buttons(self):
			ttk.Button(
				self.btn_bar, text="反相", command=self.toggle
			).pack(side="left")
			super().create_buttons()

		def apply(self):
			count = 0
			for ep, ck in self.checks:
				ep.skip = not ck.instate(("selected",))
				count += not ep.skip
			return count

		def toggle(self):
			for _ep, ck in self.checks:
				if ck.instate(("selected", )):
					ck.state(("!selected", ))
				else:
					ck.state(("selected", ))

	init_episode(mission)
	select_count = _Dialog(parent, title="選擇集數").wait()
	uninit_episode(mission)
	
	return select_count
	
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
		scale = get_scale(self.root)
		if scale < 1:
			scale = 1.0

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
		
		for domain in list_domain():
			table.add({
				"host": domain,
				"mod": domain_index[domain].name
			})
			
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

		btnstop = ttk.Button(buttonbox,text="停止下載")
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

			if get_module(url) and url != pre_url:
				pre_url = url
				self.entry_url.insert(0, url)
				self.entry_url.selection_range(0, "end")
				self.entry_url.focus_set()
		self.root.bind("<FocusIn>", trieveclipboard)

		def entrykeypress(_event):
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
				if ask_analyze_update(mission):
					mission.state = 'ANALYZE_INIT'
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
				download_manager.start_analyze(mission)

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
			missions = mission_manager.get_all_by_state("view", ("FINISHED",))
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
				if messagebox.askyesno("Comic Crawler", "確定刪除？"):
					self.remove(name, *table.selected())

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
					if select_episodes(self.root, mission):
						mission.state = "ANALYZED"

			@bind_menu("開啟資料夾")
			def _():
				for mission in table.selected():
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

			# menu call
			def tvmenucall(event):
				menu.tk_popup(event.x_root, event.y_root)
			table.tv.bind("<Button-3>", tvmenucall)

		create_menu_set("view", self.view_table)

		# library buttons
		def lib_check_update():
			download_manager.start_check_update()
		self.btn_update["command"] = lib_check_update

		def lib_download_update():
			missions = mission_manager.get_all_by_state("library", ("UPDATE",))
			if not missions:
				messagebox.showerror("Comic Crawler", "沒有新更新的任務")
				return
			mission_manager.add("view", *missions)
			download_manager.start_download()
			self.notebook.select(0)
		self.btn_download_update["command"] = lib_download_update

		# library menu
		create_menu_set("library", self.library_table)

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

class MainWindow(ViewMixin, EventMixin):
	"""Create main window GUI."""
	def __init__(self):
		"""Construct."""
		self.create_view()
		self.bind_event()
		
		self.thread = current()

		self.pool_index = {
			id(mission_manager.view): self.view_table,
			id(mission_manager.library): self.library_table
		}
		
		self.register_listeners()
		
		printer.add_listener(self.sp_callback)

		if (setting.getboolean("libraryautocheck") and
			time() - setting.getfloat("lastcheckupdate", 0) > 24 * 60 * 60):
			download_manager.start_check_update()
			
		self.update_table(mission_manager.view)
		self.update_table(mission_manager.library)
		
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
		self.root.after(int(setting.getfloat("autosave", 5) * 60 * 1000), self.save)

	def update_mission_info(self, table, mission):
		"""Update mission info on treeview."""
		if not table.contains(mission):
			return
		table.update(
			mission,
			name=safe_tk(mission.title),
			state=STATE[mission.state]
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

		@self.thread.listen("MISSION_ADDED")
		def _(event):
			mission = event.data
			
			init_episode(mission)
			if len(mission.episodes) == 1:
				uninit_episode(mission)
				return
				
			if not select_episodes(self.root, mission):
				mission_manager.remove("view", mission)

		@self.thread.listen("ANALYZE_FAILED", priority=100)
		def _(event):
			if event.target not in download_manager.analyze_threads:
				return
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
			
		@self.thread.listen("LIBRARY_CHECK_UPDATE_FAILED")
		def _(event):
			messagebox.showerror("Comic Crawler", "檢查更新未完成，已重試 10 次")
			
	def remove(self, pool_name, *missions):
		"""Wrap mission_manager.remove."""
		for mission in missions:
			if mission.state in ("DOWNLOADING", "ANALYZING"):
				messagebox.showerror("Comic Crawler", "刪除任務失敗！任務使用中")
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
					"state": STATE[mission.state]
				}, key=mission)
				
		table.rearrange(missions)
