#! python3

from tkinter import ttk

class Table:
	def __init__(self, parent, *, tv_opt={}, columns=[]):
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
			tv.heading(c["id"], text=c["text"])
			tv.column(c["id"], **{k: v for k, v in c.items() if k in ("width", "anchor")})
		tv.pack(expand=True, fill="both")
		self.tv = tv
		
		scrbar.config(command=tv.yview)
		
		self.key_index = {}
		self.iid_index = {}
		
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
