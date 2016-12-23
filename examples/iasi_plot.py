import logging
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter(
        "[%(levelname)s: %(module)s] %(message)s"))
handler.setLevel(logging.WARNING)
logging.getLogger('').setLevel(logging.WARNING)
logging.getLogger('').addHandler(handler)


from trollbufr.bufr import Bufr
from trollbufr import load_file
import numpy as np
import sys

if len(sys.argv) != 3:
    print "SYNTAX:", sys.argv[0], "<bufr> <png>"
    sys.exit(1)
testfile = sys.argv[1]
pngfile = sys.argv[2]

lon = []
lat = []
pres = []
bfr = Bufr("eccodes", "tables")
for blob, size, header in load_file.next_bufr(testfile):
    bfr.decode(blob)
    print header, bfr.get_meta()['datetime']
    for subset in bfr.next_subset():
        gotit = 0
        for k, m, (v, q) in subset.next_data():
            if gotit:
                continue
            if k == 5001:
                lat.append((0, 0, v))
            if k == 6001:
                lon.append((0, 0, v))
            if k == 7004:
                pres.append((0, 0, v))
                gotit = 1
print len(lon), len(lat), len(pres)

lons = np.concatenate(lon)
lats = np.concatenate(lat)
pres = np.concatenate(pres) / 100.0 # hPa
pres = np.ma.masked_greater(pres, 1.0e+6)

import pyresample as pr
from pyresample import kd_tree, geometry
from pyresample import utils

swath_def = geometry.SwathDefinition(lons=lons, lats=lats)
area_def = utils.parse_area_file('region_config.cfg', 'scanX')[0]

result = kd_tree.resample_nearest(swath_def, pres,
                              area_def,
                              radius_of_influence=12000,
                              epsilon=100,
                              fill_value=None)
pr.plot.save_quicklook(pngfile,
                    area_def, result, label='IASI - Cloud Top Pressure',
                    coast_res='l')

