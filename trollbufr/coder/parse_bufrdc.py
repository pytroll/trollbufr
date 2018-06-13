#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2016 Alexander Maul
#
# Author(s):
#
#   Alexander Maul <alexander.maul@dwd.de>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''
Created on Dec 07, 2016

@author:
'''

import logging
import os

from errors import BufrTableError
from tables import TabBElem

logger = logging.getLogger("trollbufr")

"""
##### Table files naming convention (Ed.3+4) #####

vssswwwwwxxxxxyyyzzz

v      - Bufr table (B, C, D)
sss    - Master table number (000)
wwwww  - Originating subcentre
xxxxx  - Originating centre
yyy    - Version number of master table used
zzz    - Version number of local table used

e.g. B0000000000098013001.TXT
     C0000000000098013001.TXT
     D0000000000098013001.TXT


##### Description of recognized table format #####

B0000000000254019001.TXT
 000001 TABLE A: ENTRY                                                   CCITTIA5                   0            0  24 CHARACTER                 0         3

C0000000000098014001.TXT
001003 0008 0000 01 ATARCTICA
            0001 01 REGION I
            0002 01 REGION II
            0003 01 REGION III
            0004 01 REGION IV
            0005 01 REGION V
            0006 01 REGION VI
            0007 01 MISSING VALUE

D0000000000098014001.TXT
 300002  2 000002
           000003

----- path/file -----
./[BCD]<3:d><7:d><3:center><3:mver><3:lver>

----- elements --- B0000000000254019001.TXT -----
# 1:sp 6:fxy 1:sp 64:name 1:sp 24:unit 1:sp 3:scale 1:sp 12:ref 1:sp 3:width
 fxy    name                                                             unit                     scale  reference width
 000001 TABLE A: ENTRY                                                   CCITTIA5                   0            0  24 [...]

----- sequence --- D0000000000098014001.TXT -----
# first line per sequence: "FXY1 N FXY2"
# following lines per seq: "       FXY2"
# N = number of FXY2 in sequence.
#
 300002  2 000002
           000003

----- code/flag --- C0000000000098014001.TXT -----
# line format:
fxy    n    code xx name
001003 0008 0000 01 ATARCTICA
            0001 01 REGION I
            0002 01 REGION II

##################################################
"""

_default_table_dir = "%s/.local/share/trollbufr" % (os.getenv('HOME'))
_table_file_names = {
    "A": "A" + "0" * 19 + ".TXT",
    "B": "B%03d%07d%03d%03d%03d.TXT",
    "C": "operator.table",
    "D": "D%03d%07d%03d%03d%03d.TXT",
    "CF": "C%03d%07d%03d%03d%03d.TXT",
}
_text_file_not_found = "Table not found: '%s'"


def load_tab_a(tables, fname):
    """Load table A (data category) from 'fname' into object Tables."""
#     if not os.path.exists(fname):
#         raise BufrTableError(_text_file_not_found % fname)
#     with open(fname, "rb") as fh:
#         for line in fh:
#             if line[0]=="#" or len(line) < 3:
#                 continue
#             d = None
#             e = None
#             lim = '|'
#             el = line.rstrip().split(lim)
#             #  0       1
#             # code|meaning
#             d = el[0]
#             e = el[1]
#             tables.tab_a[int(d)] = e
#     return True
    return False


def load_tab_b(tables, fname):
    """Load table B (elements) from 'fname' into object Tables."""
    if not os.path.exists(fname):
        raise BufrTableError(_text_file_not_found % fname)
    with open(fname, "rb") as fh:
        for line in fh:
            try:
                if line[0]=="#" or len(line) < 3:
                    continue
                e = None
                el_descr = int(line[1:7])
                el_full_name = line[8:73].rstrip()
                el_unit = line[73:98].rstrip()
                el_scale = int(line[98:101])
                el_refval = int(line[101:114])
                el_width = int(line[114:118])
                if el_unit == "CCITTIA5":
                    el_typ = "A"
                elif el_unit.startswith("CODE") or el_unit.startswith("FLAG"):
                    el_typ = el_unit[0:1]
                else:
                    el_typ = "N"
                # descr, typ, unit, abbrev, full_name, scale, refval, width
                e = TabBElem(el_descr, el_typ, el_unit, None, el_full_name, el_scale, el_refval, el_width)
                tables.tab_b[int(el_descr)] = e
            except StandardError as exc:
                logger.warning("Corrupt table %s (%s)", fname, line[0:8])
                logger.warning(exc)
    return True


def load_tab_c(tables, fname):
    """Load table C (operators) from 'fname' into object Tables."""
#     if not os.path.exists(fname):
#         raise BufrTableError(_text_file_not_found % fname)
#     with open(fname, "rb") as fh:
#         for line in fh:
#             if line[0]=="#" or len(line) < 3:
#                 continue
#             d = None
#             e = None
#             el = line.rstrip().split(',')
#             #   0       1      2                3
#             # Edition, FXY, OperatorName_en, OperationDefinition_en
#             d = el[1]
#             e = (el[2], el[3])
#             if d.endswith("YYY"):
#                 tables.tab_c[int(d[0:3])] = e
#             else:
#                 tables.tab_c[int(d)] = e
#     return True
    return False


def load_tab_d(tables, fname):
    """Load table D (sequences) from 'fname' into object Tables."""
    if not os.path.exists(fname):
        raise BufrTableError(_text_file_not_found % fname)
    with open(fname, "rb") as fh:
        desc = None
        e = []
        for line in fh:
            if line[0]=="#" or len(line) < 3:
                continue
            try:
                le = (line[1:7], line[7:10], line[10:17])
                if not le[0].isspace():
                    if len(e):
                        tables.tab_d[int(desc)] = tuple(e)
                        e = []
                    desc = le[0]
                e.append(int(le[-1]))
            except BaseException as exc:
                logger.error(exc)
                raise BufrTableError(exc)
            else:
                if len(e):
                    tables.tab_d[int(desc)] = tuple(e)
    return True


def load_tab_cf(tables, fname):
    """
    Load table CF (code- and flagtables) into object Tables.
    fname is a directory for ecCodes, a file for libDWD.
    """
    if not os.path.exists(fname):
        raise BufrTableError(_text_file_not_found % fname)
    with open(fname, "rb") as fh:
        la = ["" * 5]
        for line in fh:
            if line[0]=="#" or len(line) < 3:
                continue
            l = line.rstrip()
            try:
                le = [l[0:6], l[7:11], l[12:16], l[17:19], l[20:]]
                if le[3].isspace():
                    la[4] += le[4]
                    le = la
                if le[4].startswith("RESERVED") or le[4].startswith("NOT DEFINED"):
                    continue
                if not le[0].isspace():
                    desc = int(le[0])
                tables.tab_cf.setdefault(desc, {})[int(le[2])] = le[4]
                la = le
            except BaseException as exc:
                logger.error(exc)
                raise BufrTableError(exc)
    return True


def get_file(tabnum, base_path, master, center, subcenter, master_vers, local_vers):
    mp = lp = base_path
    m = os.path.join(mp, _table_file_names[tabnum] % (0, 0, 0, master_vers, 0))
    l = os.path.join(lp, _table_file_names[tabnum] % (0, 0, center, master_vers, local_vers))
    return (m, l)
