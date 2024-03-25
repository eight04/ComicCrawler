import os.path

from .io import path_each
from .util import safefilepath

class SavePath:
	def __init__(self, root, mission, ep, escape=safefilepath):
		self.root = root
		self.mission_title = escape(mission.title)
		self.ep_title = escape(ep.title)
		self.noepfolder = mission.module.config.getboolean(
			"noepfolder",
			fallback=getattr(mission.module, "noepfolder", False)
		)
		self.files = None
		self.escape = escape
		
	def parent(self):
		if self.noepfolder:
			return os.path.join(self.root, self.mission_title)
		return os.path.join(self.root, self.mission_title, self.ep_title)
		
	def filename(self, page, ext=""):
		"""Build filename with page and ext"""
		if not isinstance(page, str):
			page = "{:03d}".format(page)
			
		page = self.escape(page)
			
		if self.noepfolder:
			return "{ep_title}_{page}{ext}".format(
				ep_title=self.ep_title,
				page=page,
				ext=ext
			)
		return "{page}{ext}".format(
			page=page,
			ext=ext
		)
		
	def full_fn(self, page, ext=""):
		"""Build full filename with page and ext"""
		return os.path.join(self.parent(), self.filename(page, ext))

	def exists(self, page):
		"""Check if current page exists in savepath."""
		if page is None:
			return False
		
		# FIXME: if multiple SavePath is created and sharing same .parent(), 
		# they should share the .files too.
		if self.files is None:
		
			self.files = {}
			
			def build_file_table(file):
				_dir, name = os.path.split(file)
				base, ext = os.path.splitext(name)
				if ext == ".part":
					return
				self.files[base] = ext
				
			path_each(
				self.parent(),
				build_file_table
			)
			
		ext = self.files.get(self.filename(page))
		return ext and "@" not in ext
