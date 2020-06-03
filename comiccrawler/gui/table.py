#! python3

from tkinter import ttk
from functools import partial

# https://github.com/PyCQA/pylint/issues/3664
# pylint: disable=dangerous-default-value

class Table:
	def __init__(self, parent, *, tv_opt={}, columns=[]):
		self.sort_mode = None
		self.sort_on = None
		self.listeners = {}
		self.cols = {c["id"]: c for c in columns}
		
		# scrollbar
		scrbar = ttk.Scrollbar(parent)
		scrbar.pack(side="right", fill="y")
		self.scrbar = scrbar
		
		# treeview
		tv = ttk.Treeview(
			parent,
			columns=[c["id"] for c in columns if c["id"] != "#0"],
			yscrollcommand=scrbar.set,
			**tv_opt
		)
		for c in columns:
			tv.heading(c["id"], text=c["text"], command=partial(self.sort_table, id=c["id"]))
			tv.column(c["id"], **{k: v for k, v in c.items() if k in ("width", "anchor")})
		tv.pack(expand=True, fill="both")
		self.tv = tv
		
		scrbar.config(command=tv.yview)
		
		self.key_index = {}
		self.iid_index = {}
		
	def on(self, event_name, listener):
		self.listeners["on_" + event_name] = listener
		
	def sort_table(self, id=None):
		if id == "#0":
			return
		if self.sort_on == id:
			if self.sort_mode == "ASC":
				self.sort_mode = "DESC"
			else:
				self.sort_mode = "ASC"
		else:
			if self.sort_on:
				# reset text
				self.tv.heading(self.sort_on, text=self.cols[self.sort_on]["text"])
			self.sort_mode = self.cols[id].get("sort", "ASC")
			self.sort_on = id
			
		if self.sort_mode == "ASC":
			arrow = "▴"
		else:
			arrow = "▾"
		self.tv.heading(id, text=self.cols[id]["text"] + arrow)
		
		listener = self.listeners.get("on_sort")
		if listener:
			listener(self)
		
	def add(self, row, *, key=None):
		if key and key in self.key_index:
			return
		iid = self.tv.insert("", "end")
		if not key:
			key = iid
		self.key_index[key] = iid
		self.iid_index[iid] = key
		self.update(key, **row)
		return key
		
	def remove(self, *rows):
		self.tv.delete(*[self.key_index[k] for k in rows])
		for key in rows:
			if key not in self.key_index:
				continue
			iid = self.key_index[key]
			del self.key_index[key]
			del self.iid_index[iid]
		
	def clear(self, *, exclude=[]):
		keys = [key for key in self.key_index if key not in exclude]
		self.remove(*keys)
		
	def rearrange(self, rows):
		count = len(self.key_index)
		for key in rows:
			if key not in self.key_index:
				continue
			iid = self.key_index[key]
			self.tv.move(iid, "", count)
		
	def update(self, key, **kwargs):
		if key not in self.key_index:
			return
		iid = self.key_index[key]
		for column, value in kwargs.items():
			self.tv.set(iid, column, value)
			
	def selected(self):
		return [self.iid_index[i] for i in self.tv.selection()]
		
	def contains(self, key):
		return key in self.key_index
		
	def identify_row(self, y):
		iid = self.tv.identify_row(y)
		return self.iid_index.get(iid, None)
