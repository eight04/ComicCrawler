#! python3

"""Comic Crawler GUI.

"""

from tkinter import *
from tkinter.ttk import *
import tkinter.messagebox

import comiccrawler as cc
from safeprint import safeprint, addcallback
import queue

STATE = {
	cc.INIT: "準備",
	cc.ANALYZED: "解析完成",
	cc.DOWNLOADING: "下載中",
	cc.PAUSE: "停止",
	cc.FINISHED: "完成",
	cc.ERROR: "錯誤",
	cc.INTERRUPT: "已刪除",
	cc.UPDATE: "有更新",
	cc.ANALYZING: "分析中"
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

	# def buttonbox(self):
		# """add standard button box. 
		
		# override if you don't want the standard buttons
		# """

		# box = Frame(self)

		# Button(box, text="確定", command=self.ok, default=ACTIVE).pack(side="left")
		# Button(box, text="取消", command=self.cancel).pack(side="left")

		# self.bind("<Return>", self.ok)
		# self.bind("<Escape>", self.cancel)

		# box.pack()
		
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
	
class MainWindow(cc.Controller):
	"""Main GUI window class."""
		
	def view(self):
		"""Draw the window."""
		self.gRoot = Tk()
		
		# ========GUI START========

		self.gRoot.title("Comic Crawler")
		self.gRoot.geometry("500x400")
		
		Label(self.gRoot,text="輸入連結︰").pack(anchor="w")
		
		# url entry
		entry_url = Entry(self.gRoot)
		entry_url.pack(fill="x")
		self.gEntry_url = entry_url
		
		# bunch of buttons
		buttonbox = Frame(self.gRoot)
		buttonbox.pack()
		
		btnaddurl = Button(buttonbox, text="加入連結")
		btnaddurl.pack(side="left")
		self.gBtnaddurl = btnaddurl
		
		btnstart = Button(buttonbox, text="開始下載")
		btnstart.pack(side="left")
		self.gBtnstart = btnstart
		
		btnstop = Button(buttonbox,text="停止下載")
		btnstop.pack(side="left")
		self.gBtnstop = btnstop
			
		btnclean = Button(buttonbox, text="移除已完成")
		btnclean.pack(side="left")
		self.gBtnclean = btnclean		
		
		btnconfig = Button(buttonbox, text="重載設定檔")
		btnconfig.pack(side="left")
		self.gBtnconfig = btnconfig
		
		# notebook
		self.gNotebook = Notebook(self.gRoot)
		self.gNotebook.pack(expand=True, fill="both")
		
		# download manager
		frame = Frame(self.gNotebook)
		self.gNotebook.add(frame, text="任務列表")
		
		# mission list
		tv = Treeview(frame, columns=("name","host","state"))
		tv.heading("#0", text="#")
		tv.heading("name", text="任務")
		tv.heading("host", text="主機")
		tv.heading("state", text="狀態")
		tv.column("#0", width="25")
		tv.column("host", width="50", anchor="center")
		tv.column("state", width="70", anchor="center")
		tv.pack(expand=True, fill="both")
		self.gTv = tv
		
		# mission context menu
		tvmenu = Menu(tv, tearoff=False)
		tvmenu.add_command(label="刪除")
		tvmenu.add_command(label="移至頂部")
		tvmenu.add_command(label="移至底部")
		tvmenu.add_command(label="改名")
		tvmenu.add_command(label="加入圖書館")
		tvmenu.add_command(label="重新選擇集數")
		self.gTvmenu = tvmenu
		
		# library
		frame = Frame(self.gNotebook)
		self.gNotebook.add(frame, text="圖書館")
		
		# library buttons
		btnBar = Frame(frame)
		btnBar.pack()
		
		self.gBtnUpdate = Button(btnBar, text="檢查更新")
		self.gBtnUpdate.pack(side="left")
		
		self.gBtnDownloadUpdate = Button(btnBar, text="下載更新")
		self.gBtnDownloadUpdate.pack(side="left")
		
		# library list
		self.gLibTV = Treeview(frame, columns=("name","host","state"))
		self.gLibTV.heading("#0", text="#")
		self.gLibTV.heading("name", text="任務")
		self.gLibTV.heading("host", text="主機")
		self.gLibTV.heading("state", text="狀態")
		self.gLibTV.column("#0", width="25")
		self.gLibTV.column("host", width="50", anchor="center")
		self.gLibTV.column("state", width="70", anchor="center")
		self.gLibTV.pack(expand=True, fill="both")
		
		# library context menu
		self.gLibMenu = Menu(self.gLibTV, tearoff=False)
		self.gLibMenu.add_command(label="刪除")
		self.gLibMenu.add_command(label="重新選擇集數")
	
		# status bar
		statusbar = Label(self.gRoot, text="Comic Crawler", anchor="e")
		statusbar.pack(anchor="e")
		self.gStatusbar = statusbar
		
		# ========GUI END========
		
		self.bindevent()
		self.messageq = queue.Queue()
		addcallback(self.sendToBucket)
		self.tkloop()
		self.gRoot.mainloop()
		
	def sendToBucket(self, text):
		"""hook with safeprint"""
		
		cc._evtcallback("MESSAGE", text)
		
	def tkloop(self):
		"""get message from comiccrawler.messageBucket"""
		
		try:
			while True:
				message, args = cc.messageBucket.get_nowait()
				self.message(message, args)
		except queue.Empty:
			pass
			
		self.gRoot.after(100, self.tkloop)

	def bindevent(self):
		"""Bind events"""
		
		# something about entry
		_presp = ""
		def trieveclipboard(event):
			nonlocal _presp
			try:
				s = self.gRoot.clipboard_get(type="STRING")
			except Exception:
				return
			sp = self.gEntry_url.get()
			if not sp and self.moduleManager.validUrl(s) and s != _presp:
				self.gEntry_url.insert(0, s)
				self.gEntry_url.selection_range(0, "end")
				_presp = s
				self.gEntry_url.focus_set()
		self.gRoot.bind("<FocusIn>", trieveclipboard)	
		
		def entrykeypress(event):
			addurl()
		self.gEntry_url.bind("<Return>", entrykeypress)
		
		# interface for download manager
		def addurl():
			self.iAddUrl(self.gEntry_url.get())
			self.gEntry_url.delete(0, "end")
		self.gBtnaddurl["command"] = addurl
		
		def startdownload():
			self.iStart()
		self.gBtnstart["command"] = startdownload
		
		def stopdownload():
			self.iStop()
		self.gBtnstop["command"] = stopdownload
		
		def cleanfinished():
			self.iClean()
		self.gBtnclean["command"] = cleanfinished
		
		def reloadconfig():
			self.iReloadConfig()
		self.gBtnconfig["command"] = reloadconfig
		
		# interface for mission list
		def tvdelete():
			if tkinter.messagebox.askyesno("Comic Crawler", "確定刪除？"):
				s = self.gTv.selection()
				self.iRemoveMission(*[self.iidholder[k] for k in s])
		self.gTvmenu.entryconfig(0, command=tvdelete)
		
		def tvlift():
			s = self.gTv.selection()
			self.iLift(*[self.iidholder[k] for k in s])
		self.gTvmenu.entryconfig(1, command=tvlift)
			
		def tvdrop():
			s = self.gTv.selection()
			self.iDrop(*[self.iidholder[k] for k in s])
		self.gTvmenu.entryconfig(2, command=tvdrop)
		
		def tvchangetitle():
			s = self.gTv.selection()
			mission = self.iidholder[s[0]]
			selectTitle(self.gRoot, mission)
		self.gTvmenu.entryconfig(3, command=tvchangetitle)
		
		def tvAddToLib():
			s = self.gTv.selection()
			# mission = self.iidholder[s[0]]
			missions = [ self.iidholder[i] for i in s ]
			titles = [ m.title for m in missions ]
			for mission in missions:
				self.iAddToLib(mission)
			safeprint("已加入圖書館︰{}".format(", ".join(titles)))
		self.gTvmenu.entryconfig(4, command=tvAddToLib)
		
		def tvReselectEP():
			s = self.gTv.selection()
			# mission = self.iidholder[s[0]]
			missions = [ self.iidholder[i] for i in s ]
			titles = [ m.title for m in missions ]
			for mission in missions:
				selectEp(self.gRoot, mission)
		self.gTvmenu.entryconfig(5, command=tvReselectEP)
		
		def tvmenucall(event):
			self.gTvmenu.post(event.x_root, event.y_root)
		self.gTv.bind("<Button-3>", tvmenucall)
		
		# interface for library
		def libCheckUpdate():
			self.iLibCheckUpdate()
		self.gBtnUpdate["command"] = libCheckUpdate
		
		def libDownloadUpdate():
			self.iLibDownloadUpdate()
			self.gNotebook.select(0)
			self.iStart()
		self.gBtnDownloadUpdate["command"] = libDownloadUpdate
		
		# interface for library list
		def libMenuDelete():
			if tkinter.messagebox.askyesno("Comic Crawler", "確定刪除？"):
				s = self.gLibTV.selection()
				self.iLibRemove(*[self.libIdIndex[k] for k in s])
		self.gLibMenu.entryconfig(0, command=libMenuDelete)
		
		def libMenuReselectEP():
			s = self.gLibTV.selection()
			missions = [self.libIdIndex[k] for k in s]
			for mission in missions:
				selectEp(self.gRoot, mission)
		self.gLibMenu.entryconfig(1, command=libMenuReselectEP)
		
		def libMenuCall(event):
			self.gLibMenu.post(event.x_root, event.y_root)
		self.gLibTV.bind("<Button-3>", libMenuCall)
		
		# close window event
		def beforequit():
			if (self.downloadManager.running and 
					not tkinter.messagebox.askokcancel("Comic Crawler",
						"任務下載中，確定結束？")):
				return
			self.downloadManager.stop()
			self.gRoot.destroy()
		self.gRoot.protocol("WM_DELETE_WINDOW", beforequit)
		
		
	def addtotree(self, mission):
		"""Add item into treeview."""

		downloader = mission.downloader
		m = mission
		cid = self.gTv.insert("","end",
				values=(m.title, downloader.name, STATE[m.state]))
		self.iidholder[cid] = m
			
	def load(self):
		"""load mission from mission que"""
		
		missionlist = self.downloadManager.missionque.q
		for m in missionlist:
			self.addtotree(m)
	
	def tvrefresh(self):
		"""refresh treeview"""

		ids = self.gTv.get_children()
		self.gTv.delete(*ids)
		self.iidholder = {}
		self.load()
		
	def libTvRefresh(self):
		"""refresh lib treeview"""
		
		tv = self.gLibTV
		ids = tv.get_children()
		tv.delete(*ids)
		self.libIdIndex = {}
		list = self.library.libraryList.q
		for m in list:
			cid = tv.insert("","end",
				values=(m.title, m.downloader.name, STATE[m.state]))
			self.libIdIndex[cid] = m
		
	def iAnalyzeFinished(self, mission, error=None, er_msg=None):
		"""overwrite, send to message bucket"""
		
		cc._evtcallback("ANALYZED_FINISHED", mission, error, er_msg)
	
	def message(self, msg, args=None):
		"""GUI Message control"""
		
		if msg is "MESSAGE":
			text, = args
			self.gStatusbar["text"] = text
	
		elif msg is "MISSION_STATE_CHANGE":
			self.tvrefresh()
			self.libTvRefresh()

		elif msg is "MISSION_TITLE_CHANGE":
			self.tvrefresh()
			self.libTvRefresh()

		elif msg is "MISSIONQUE_ARRANGE":
			self.tvrefresh()
			self.libTvRefresh()
			
		elif msg is "WORKER_TERMINATED":
			mission, er, er_msg = args
			
			tkinter.messagebox.showerror(
				"Comic Crawler", "下載中斷！\n{}".format(er_msg))
				
		elif msg is "ANALYZED_FINISHED":
			mission, error, er_msg = args
			
			if error:
				tkinter.messagebox.showerror(
					"Comic Crawler", "解析錯誤！\n{}".format(er_msg))
				return
				
			if len(mission.episodelist) > 1 and not selectEp(self.gRoot, mission):
				return
				
			self.iAddMission(mission)
				
		else:
			pass

def selectTitle(parent, mission):
	"""change mission title dialog"""
	
	w = Dialog(parent)
	
	entry = Entry(w.body)
	entry.insert(0, mission.title)
	entry.selection_range(0, "end")
	entry.pack()
	
	entry.focus_set()
	
	def apply():
		title = entry.get()
		mission.setTitle(title)
		
	w.apply = apply
	
	ret = w.wait()
	return ret
	
def selectEp(parent, mission):
	"""select episode dialog"""
	
	w = Dialog(parent)
	
	xscrollbar = Scrollbar(w.body, orient="horizontal")
	canvas = Canvas(w.body, xscrollcommand=xscrollbar.set, highlightthickness="0")
	inner = Frame(canvas)
	
	# list of checkbutton
	vs = []
	i = 0
	
	# make checkbutton into inner frame
	for ep in mission.episodelist:
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
	for i in range(ceil(len(mission.episodelist) / 20)):
		ck = Checkbutton(inner)
		ck.state(("!alternate", "selected"))
		# print(ck.state())
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
		w.result = len([ i for i in mission.episodelist if not i.skip ])
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

if __name__ == "__main__":
	MainWindow()
