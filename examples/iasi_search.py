from trollbufr.bufr import Bufr
from trollbufr import load_file

import sys
import glob
import logging
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter(
        "[%(levelname)s: %(module)s] %(message)s"))
# handler.setLevel(logging.DEBUG)
# logging.getLogger('').setLevel(logging.DEBUG)
handler.setLevel(logging.WARNING)
logging.getLogger('').setLevel(logging.WARNING)
logging.getLogger('').addHandler(handler)

fp = sys.argv[1]

bfr = Bufr("eccodes", "tables")
for fn in glob.glob(fp):
    print fn
    i=0
    for blob, size, header in load_file.next_bufr(fn):
        try:
            bfr.decode(blob)
            lon = lat = 0
            for subset in bfr.next_subset():
                for k, m, (v, q) in subset.next_data():
                    if k == 5001:
                        lat = v
                    if k == 6001:
                        lon = v
                break

            if header.startswith("IEDX"):
                print i,header, lon, lat,
                if lon > -10 and lon < 30 and lat > 50 and lat < 70:
                    print "<------"
                else:
                    print
        except StandardError as e:
            print "ERR:",e
        i+=1
print "---"
