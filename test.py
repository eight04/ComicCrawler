#! python3

test = {
	0: "X",
	"0": "Y"
}

print(test)

from comiccrawler import grabhtml

header = {
	# "Referer": "https://chan.sankakucomplex.com/post/show/1095036",
	# "User-Agent": "Mozilla/5.0 (Windows NT 6.1; WOW64; rv:32.0) Gecko/20100101 Firefox/32.0",
	"Cookie": "cf_clearance=164e92b204e021cf634c2b03f6c028abc7880c83-1412522413-14400;"
		# "__cfduid:	de7b794fd64f66e63c8d8183430c9281d1412518380460"
}
grabhtml("https://cs.sankakucomplex.com/data/19/4c/194cff7eb95add57b013a2337827435d.png?1095036", header)
