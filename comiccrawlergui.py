#! python3

"""Comic Crawler GUI.

"""

import threading

from tkinter import *
from tkinter.ttk import *
import tkinter.messagebox

import comiccrawler as cc
import safeprint
import queue

STATE = {
	cc.INIT: "準備",
	cc.ANALYZED: "解析完成",
	cc.DOWNLOADING: "下載中",
	cc.PAUSE: "停止",
	cc.FINISHED: "完成",
	cc.ERROR: "錯誤",
	cc.INTERRUPT: "已刪除"
}

class Dialog(Toplevel):
	def __init__(self, parent, title=None):
		super().__init__(parent)
		# self.group(parent)
		# self.geometry("+{}+{}".format(parent.winfo_rootx()+50,
                                  # parent.winfo_rooty()+50))
		
		if title:
			self.title(title)
		self.parent = parent
		self.result = None
		
		self.body = Frame(self)
		self.body.pack()
		
		box = Frame(self)
		Button(box, text="確定", command=self.ok, default=ACTIVE).pack(side="left")
		Button(box, text="取消", command=self.cancel).pack(side="left")
		box.pack()
		self.buttonbox = box

		self.bind("<Return>", self.ok)
		self.bind("<Escape>", self.cancel)

		self.grab_set()
		self.protocol("WM_DELETE_WINDOW", self.cancel)
		self.focus_set()

	def buttonbox(self):
		# add standard button box. override if you don't want the
		# standard buttons

		box = Frame(self)

		Button(box, text="確定", command=self.ok, default=ACTIVE).pack(side="left")
		Button(box, text="取消", command=self.cancel).pack(side="left")

		self.bind("<Return>", self.ok)
		self.bind("<Escape>", self.cancel)

		box.pack()
		
	def ok(self, event=None):

		if not self.validate():
			self.initial_focus.focus_set() # put focus back
			return

		self.withdraw()
		self.update_idletasks()

		self.apply()
		self.cancel()

	def cancel(self, event=None):

		# put focus back to the parent window
		self.parent.focus_set()
		self.destroy()

	def validate(self):
		return 1 # override

	def apply(self):
		pass # override

	def wait(self):
		self.wait_window(self)
		return self.result
	
class MainWindow(Tk):
	"""Main GUI window class."""
		
	def __init__(self):
		"""Draw the widgets."""
		super(MainWindow, self).__init__()

		self.title("Comic Crawler")
		self.geometry("500x400")
		
		Label(self,text="輸入連結︰").pack(anchor="w")
		
		entry_url = Entry(self)
		entry_url.pack(fill="x")
		self.entry_url = entry_url
		
		buttonbox = Frame(self)
		buttonbox.pack()
		
		btnaddurl = Button(buttonbox, text="加入連結")
		btnaddurl.pack(side="left")
		self.btnaddurl = btnaddurl
		
		btnstart = Button(buttonbox, text="開始下載")
		btnstart.pack(side="left")
		self.btnstart = btnstart
		
		btnstop = Button(buttonbox,text="停止下載")
		btnstop.pack(side="left")
		self.btnstop = btnstop
			
		btnclean = Button(buttonbox, text="移除已完成")
		btnclean.pack(side="left")
		self.btnclean = btnclean		
		
		btnconfig = Button(buttonbox, text="重載設定檔")
		btnconfig.pack(side="left")
		self.btnconfig = btnconfig
		
		Label(self,text="任務列表︰").pack(anchor="w")
		
		tv = Treeview(self, columns=("name","host","state"))
		tv.heading("#0", text="#")
		tv.heading("name", text="任務")
		tv.heading("host", text="主機")
		tv.heading("state", text="狀態")
		tv.column("#0", width="25")
		tv.column("host", width="50", anchor="center")
		tv.column("state", width="70", anchor="center")
		tv.pack(expand=True, fill="both")
		self.tv = tv
		
		tvmenu = Menu(tv, tearoff=False)
		tvmenu.add_command(label="刪除")
		tvmenu.add_command(label="移至頂部")
		tvmenu.add_command(label="移至底部")
		tvmenu.add_command(label="改名")
		self.tvmenu = tvmenu
	
		statusbar = Label(self, text="Comic Crawler", anchor="e")
		statusbar.pack(anchor="e")
		self.statusbar = statusbar
		
		self.messageq = queue.Queue()
		self.iidholder = {}
		
	def tkloop(self):
		try:
			while True:
				f, a = self.messageq.get_nowait()
				f(*a)
		except queue.Empty:
			pass
		# except Exception as er:
			# safeprint.safeprint("Tkloop error: {}".format(er))
			
		self.after(100, self.tkloop)
		
	def mainloop(self):
		self.tkloop()
		super().mainloop()
		
	def bindevent(self):
		"""Binding event. Should I try to implement together?"""
		
		_presp = ""
		def trieveclipboard(event):
			nonlocal _presp
			try:
				s = self.clipboard_get(type="STRING")
			except Exception:
				return
			sp = self.entry_url.get()
			if not sp and dlmm.validUrl(s) and s != _presp:
				self.entry_url.insert(0, s)
				self.entry_url.selection_range(0, "end")
				_presp = s
				self.entry_url.focus_set()
		self.bind("<FocusIn>", trieveclipboard)	
		
		def entrykeypress(event):
			addurl()
		self.entry_url.bind("<Return>", entrykeypress)
		
		def addurl():
			u = self.entry_url.get()
			downloader = dlmm.getDownloader(u)
			if downloader is None:
				tkinter.messagebox.showerror("Comic Crawler","不支援的網址")
			else:
				m = cc.Mission()
				m.url = u
				m.downloader = downloader
				_status("Trieving url: {}".format(m.url))

				crawler.analyze(m)

			self.entry_url.delete(0, len(u))
		self.btnaddurl["command"] = addurl
		
		def startdownload():
			crawler.start()
		self.btnstart["command"] = startdownload
		
		def stopdownload():
			crawler.stop()
		self.btnstop["command"] = stopdownload
		
		def cleanfinished():
			crawler.missionque.cleanfinished()
		self.btnclean["command"] = cleanfinished
		
		def reloadconfig():
			dlmm.loadconfig()
			crawler.loadconfig()
		self.btnconfig["command"] = reloadconfig
		
		def tvdelete():
			if tkinter.messagebox.askyesno("Comic Crawler", "確定刪除？"):
				s = self.tv.selection()
				crawler.missionque.remove([self.iidholder[k] for k in s])
		self.tvmenu.entryconfig(0, command=tvdelete)
		
		def tvlift():
			s = self.tv.selection()
			crawler.missionque.lift([self.iidholder[k] for k in s])
		self.tvmenu.entryconfig(1, command=tvlift)
			
		def tvdrop():
			s = self.tv.selection()
			crawler.missionque.drop([self.iidholder[k] for k in s])
		self.tvmenu.entryconfig(2, command=tvdrop)
		
		def tvchangetitle():
			s = self.tv.selection()
			mission = self.iidholder[s[0]]
			# selectTitle(self.iidholder[s[0]])
			selectTitle(mission)
		self.tvmenu.entryconfig(3, command=tvchangetitle)
	
		def tvmenucall(event):
			self.tvmenu.post(event.x_root, event.y_root)
		self.tv.bind("<Button-3>", tvmenucall)
		
		# close window event
		def beforequit():
			if crawler.state == cc.PAUSE or tkinter.messagebox.askokcancel(
					"Comic Crawler", "任務下載中，確定結束？"):
				crawler.stop()
				self.destroy()
		self.protocol("WM_DELETE_WINDOW", beforequit)
		
		def _qstatus(str):
			self.messageq.put((_status, (str, )))
			
		def _status(str):
			self.statusbar["text"] = str
		safeprint.addcallback(_qstatus)
		
		
	def addtotree(self, mission):
		"""Add item into treeview."""
		
		downloader = mission.downloader
		m = mission
		cid = self.tv.insert("","end",
				values=(m.title, downloader.name, STATE[m.state]))
		self.iidholder[cid] = m
			
	def load(self):
		"""load mission from mission que"""
		
		missionlist = crawler.missionque.q
		for m in missionlist:
			self.addtotree(m)
	
	def tvrefresh(self):
		"""refresh treeview"""
		
		ids = self.tv.get_children()
		self.tv.delete(*ids)
		self.iidholder = {}
		self.load()
	
	def message(self, msg, *arg):
		"""GUI Message control"""
		
		if msg is "ANALYZED_SUCCESS":
			def _(mission):
				if len(mission.episodelist) > 1 and not selectEp(mission):
					return
				crawler.addmission(mission)
				safeprint.safeprint("Queued mission: {}".format(mission.title))
			self.messageq.put((_, arg))

		elif msg is "ANALYZED_FAILED":
			def _(mission, er):
				tkinter.messagebox.showerror(
					"Comic Crawler", "解析錯誤！\n{}".format(er))
			self.messageq.put((_, arg))
			
		elif msg is "MISSION_STATE_CHANGE":
			def _(mission):
				for k in self.iidholder:
					if self.iidholder[k] is mission:
						cid = k
						break
						
				self.tv.set(cid, "state", STATE[mission.state])
				if mission.state is cc.FINISHED:
					self.tv.item(cid, tags=["f"])
			self.messageq.put((_, arg))
				
		elif msg is "MISSION_TITLE_CHANGE":
			def _(mission):
				for k in self.iidholder:
					if self.iidholder[k] is mission:
						cid = k
						break
						
				self.tv.set(cid, "name", mission.title)
			self.messageq.put((_, arg))
			
		elif msg is "MISSIONQUE_ARRANGE":
			def _():
				self.tvrefresh()
			self.messageq.put((_, arg))
			
		elif msg is "WORKER_TERMINATED":
			def _(mission, er, er_msg):
				tkinter.messagebox.showerror(
					"Comic Crawler", "下載中斷！\n{}".format(er_msg))
			self.messageq.put((_, arg))
		else:
			pass

def selectTitle(mission):
	w = Dialog(root)
	
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
	
def selectEp(mission):
	w = Dialog(root)
	
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

"""
def selectEp_(mission):
	""Show selecting episodes panel.""

	# create new window
	w = Toplevel()
	
	# scrollbar
	xscrollbar = Scrollbar(w, orient="horizontal")
	
	# scrolling canvas and inner frame
	canvas = Canvas(w, xscrollcommand=xscrollbar.set, highlightthickness="0")
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
	
	# buttons container
	lb = Frame(w)
	
	def inselectep():
		for v in vs:
			ck, ep = v
			ep.skip = not ck.instate(("selected",))
		w.destroy()
		
	cancel_ = False
	def cancel():
		nonlocal cancel_
		cancel_ = True
		w.destroy()
	
	def toggle():
		for v in vs:
			ck, ep = v
			if ck.instate(("selected", )):
				ck.state(("!selected", ))
			else:
				ck.state(("selected", ))
	
	Button(lb, text="反相", command=toggle).pack(side="left")
	Button(lb, text="確定", command=inselectep).pack(side="left")
	Button(lb, text="取消", command=cancel).pack(side="left")
	
	# show button container
	lb.pack()
	
	# wait window close
	w.wait_window(w)
	
	if cancel_:
		return -1
"""


if __name__ == "__main__":

	root = MainWindow()
	dlmm = cc.DLModuleManager()
	crawler = cc.ComicCrawler(dlmm, root.message)
		
	root.bindevent()
	
	crawler.load()
	root.load()
	
	root.mainloop()
	
	if crawler.thread:
		crawler.thread.join()	
		
	crawler.save()
	
