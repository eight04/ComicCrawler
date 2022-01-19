#! python3
import webbrowser
import tkinter as tk
from tkinter import ttk

from belfrywidgets import ToolTip

from .core import safe_tk
from .dialog import Dialog

class SelectEpisodeDialog(Dialog):
	def __init__(self, parent, title=None, mission=None, on_closed=None):
		self.mission = mission
		
		self.checks = []
		self.anchor_index = None
		
		self.canvas = None
		self.window = None
		self.window_column = 0
		self.window_left = 0
		self.style = None
		
		super().__init__(parent, title, on_closed=on_closed)
		
	def create_window(self, column):
		if self.window:
			self.window.update_idletasks()
			self.window_left += self.window.winfo_reqwidth()
			self.window_column = column
			
		self.window = ttk.Frame(self.canvas)
		self.canvas.create_window((self.window_left, 0), window=self.window,
			anchor="nw")
			
	def create_checkbutton(self, ep, index):
		# click handler for range selection
		def handle_click(event):
			if event.state & 0x0001 and self.anchor_index is not None: # shift
				start = min(self.anchor_index, index)
				end = max(self.anchor_index, index)
				for i in range(start, end + 1):
					if i in (index, self.anchor_index):
						continue
					check = self.checks[i]
					if check.instate(("selected", )):
						check.state(("!selected", ))
					else:
						check.state(("selected", ))
			else:
				self.anchor_index = index

		def handle_right_click(_event):
			webbrowser.open(ep.url)
				
		style = "TCheckbutton"
		if ep.complete:
			style = "Complete.TCheckbutton"
		check = ttk.Checkbutton(self.window, text=safe_tk(ep.title), style=style)
		check.bind("<ButtonRelease-1>", handle_click)
		check.bind("<ButtonRelease-3>", handle_right_click)
		check.state(("!alternate",))
		if not ep.skip:
			check.state(("selected",))
		check.grid(
			column=(index // 20) - self.window_column,
			row=index % 20,
			sticky="w"
		)
		self.checks.append(check)
		
	def create_column_checkbutton(self, index):
		def check_col():
			start_index = index // 20 * 20
			if check.instate(("selected",)):
				state = ("selected",)
			else:
				state = ("!selected",)
			for ep_check in self.checks[start_index:index + 1]:
				ep_check.state(state)
				
		check = ttk.Checkbutton(self.window, command=check_col)
		state = ("!alternate",)
		if self.mission.module.config.getboolean("selectall"):
			state += ("selected",)
		check.state(state)
		check.grid(
			column=(index // 20) - self.window_column,
			row=20,
			sticky="we"
		)

	def create_body(self):
		self.style = ttk.Style()
		self.style.configure("Complete.TCheckbutton", foreground="green")

		xscrollbar = ttk.Scrollbar(self.body, orient="horizontal")
		self.canvas = tk.Canvas(
			self.body,
			xscrollcommand=xscrollbar.set,
			highlightthickness="0"
		)

		for i, ep in enumerate(self.mission.episodes):
			# create a new window for every 200 items
			if i % 200 == 0:
				self.create_window(i // 20)
			
			# create checkbutton
			self.create_checkbutton(ep, i)
			
			# checkbutton for each column
			if i % 20 == 19 or i == len(self.mission.episodes) - 1:
				self.create_column_checkbutton(i)
				
		# Resize canvas
		self.canvas.update_idletasks()
		cord = self.canvas.bbox("all")
		self.canvas.config(
			scrollregion=cord,
			height=cord[3],
			width=cord[2]
		)

		# caculates canvas's size then deside whether to show scrollbar
		def decide_scrollbar(_event):
			if self.canvas.winfo_width() >= self.canvas.winfo_reqwidth():
				xscrollbar.pack_forget()
				self.canvas.unbind("<Configure>")
		self.canvas.bind("<Configure>", decide_scrollbar)

		# draw innerframe on canvas then show
		self.canvas.pack()

		# link scrollbar to canvas then show
		xscrollbar.config(command=self.canvas.xview)
		xscrollbar.pack(fill="x")
		
	def create_buttons(self):
		btn = ttk.Button(self.btn_bar, text="反相", command=self.toggle)
		btn.pack(side="left")
		ToolTip(btn, "點擊任意項目後，Shift + 點擊另一項目，會對其間的項目反相")
		super().create_buttons()

	def apply(self):
		count = 0
		for ep, ck in zip(self.mission.episodes, self.checks):
			ep.skip = not ck.instate(("selected",))
			count += not ep.skip
		return count

	def toggle(self):
		for ck in self.checks:
			if ck.instate(("selected", )):
				ck.state(("!selected", ))
			else:
				ck.state(("selected", ))
		
def select_episodes(parent, mission, on_closed=None):
	"""Create dialog to select episodes."""
	dialog = SelectEpisodeDialog(
		parent,
		title="選擇集數",
		mission=mission,
		on_closed=on_closed
	)
	if on_closed:
		return None
	return dialog.wait()
