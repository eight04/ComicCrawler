#! python3

import tkinter as tk
from tkinter import ttk

from .core import safe_tk

class Dialog:
	def __init__(self, parent, title="Dialog"):
		self.parent = parent
		self.result = None
	
		# root
		self.root = tk.Toplevel(parent)
		self.root.title(safe_tk(title))
		
		# body
		self.body = ttk.Frame(self.root)
		self.create_body()
		self.body.pack()
		
		# button bar
		self.btn_bar = ttk.Frame(self.root)
		self.create_buttons()
		self.btn_bar.pack()
		
		# bind event
		self.root.bind("<Return>", self.resolve)
		self.root.bind("<Escape>", self.reject)
		
		# show dialog and disable parent
		self.root.grab_set()
		self.root.protocol("WM_DELETE_WINDOW", self.reject)
		self.root.focus_set()
		
	def create_body(self):
		ttk.Label(self.body, text="Default dialog").pack()
		
	def create_buttons(self):
		ttk.Button(
			self.btn_bar, text="確定", command=self.resolve, default="active"
		).pack(side="left")
		ttk.Button(
			self.btn_bar, text="取消", command=self.reject
		).pack(side="left")
		
	def resolve(self, _event=None):
		"""Apply and destroy dialog."""
		self.root.update_idletasks()
		self.result = self.apply()
		self.parent.focus_set()
		self.root.destroy()
		
	def reject(self, _event=None):
		"""Destroy dialog."""
		self.parent.focus_set()
		self.root.destroy()
		
	def apply(self):
		return True
		
	def wait(self):
		"""Wait the dialog to close."""
		self.root.wait_window(self)
		return self.result
