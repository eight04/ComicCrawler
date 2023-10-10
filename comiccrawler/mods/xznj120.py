#! python3

"""this is xznj120 module for comiccrawler

Example:
	http://www.xznj120.com/lianai/591/
	http://www.33am.cn/gushi/2026/
	http://www.36rm.cn/lianai/235/

"""

from html import unescape
import re

from deno_vm import eval

from ..url import urljoin
from ..core import Episode, grabhtml

domain = ["www.xznj120.com", "www.33am.cn", "www.36rm.cn"]
name = "受漫畫"

def get_title(html, url):
	return re.search("<h1>([^<]+)", html).group(1)

def get_episodes(html, url):
	s = []
	for match in re.finditer(r'<li><a href="([^"]+)"[^>]+><p>([^<]+)', html):
		ep_url, title = [unescape(t) for t in match.groups()]
		s.append(Episode(title, urljoin(url, ep_url)))
	return s[::-1]
	
def get_images(html, url):
	script = re.search(r'<script>\s*(var qTcms_Cur[\s\S]+?)</script>', html).group(1)
	show_js_src = re.search(r'src="([^"]+?show\.\d+\.js[^"]*)', html).group(1)
	show_js = grabhtml(urljoin(url, show_js_src))
	real_pic_fn = re.search(r'(function f_qTcms_Pic_curUrl_realpic[\s\S]+?)function', show_js).group(1)
	code = """
	{script}
	{real_pic_fn}
	function base64_decode(data) {{
		return Buffer.from(data, "base64").toString();
	}}
	// m.wuyouhui.net/template/wap1/css/d7s/js/show.20170501.js?20190506201115
	Buffer.from(qTcms_S_m_murl_e, "base64")
		.toString()
		.split("$qingtiandy$")
		.filter(u => !/^(--|\+)/.test(u))
		.map(f_qTcms_Pic_curUrl_realpic);
	""".format(script=script, real_pic_fn=real_pic_fn)
	return [urljoin(url, i) for i in eval(code)]
