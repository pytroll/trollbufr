import logging
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter(
        "[%(levelname)s: %(module)s] %(message)s"))
handler.setLevel(logging.WARNING)
logging.getLogger('').setLevel(logging.WARNING)
logging.getLogger('').addHandler(handler)


from trollbufr.bufr import Bufr
from trollbufr import load_file
import sys

if len(sys.argv) != 2:
    print "SYNTAX:", sys.argv[0], "<bufr>"
    sys.exit(1)
testfile = sys.argv[1]

bfr = Bufr("eccodes", "tables")
for blob, size, header in load_file.next_bufr(testfile):
    bfr.decode(blob)
    print "\n", testfile, header, "\n", bfr.get_meta_str()
    for subset in bfr.next_subset():
        for k, m, (v, q) in subset.next_data():
            print k, m, v
        break

    with open(header.replace(" ","_"), "w") as fh:
        fh.write(blob[0:])
