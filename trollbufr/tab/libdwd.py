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
Created on Sep 15, 2016

@author: amaul
'''

import logging
import os

from errors import BufrTableError
from tables import TabBelem

logger = logging.getLogger("trollbufr")

"""
##### Description of recognized table format =libdwd= #####

----- path/file -----
./
./local_CENTRE_SUBCENTRE/

----- table_b_VVV -----
  0          1           2         3            4                 5                    6
"FXY<tab>libDWDType<tab>unit<tab>scale<tab>referenceValue<tab>dataWidth_Bits<tab>descriptor_name<lf>"
000001  A       CCITT IA5       0       0       24      TABLE A: ENTRY

----- table_d_VVV -----
# first line per sequence: "FXY1<tab>FXY2<lf>"
# following lines per seq: "<tab>FXY2<lf>"
#
300002  000002
        000003

----- codeflags_VVV -----
                 0          1                 2                3               4              5                  6
# line format: "FXY<tab>libDWDType<tab>codeFigureFrom<tab>codeFigureTo<tab>entryname<tab>entryNameSub1<tab>entryNameSub2<lf>"
001003  C       0               Antarctica
001003  C       1               Region I

----- operator.table -----
#Edition, FXY, OperatorName_en, OperationDefinition_en
3,201YYY, Change data width, Add (YYY-128) bits to the data width given for each data element in Table B

----- common code tables -----
#code|meaning
0|Surface data - land

###########################################################
"""

_table_file_names = {
            "A": "datacat.table",
            "B": "table_b_%03d",
            "C": "operator.table",
            "D": "table_d_%03d",
            "CF": "codeflags_%03d",
        }
_text_file_not_found = "Table not found: '%s'"

def load_tab_a(tables, fname):
    """Load table A (data category) from 'fname' into object Tables."""
    if not os.path.exists(fname):
        raise BufrTableError(_text_file_not_found % fname)
    with open(fname, "rb") as fh:
        for line in fh:
            if line.startswith('#') or len(line) < 3:
                continue
            d = None
            e = None
            lim = '|'
            el = line.rstrip().split(lim)
            #  0       1
            # code|meaning
            d = el[0]
            e = el[1]
            tables.tab_a[int(d)] = e
    return True

def load_tab_b(tables, fname):
    """Load table B (elements) from 'fname' into object Tables."""
    if not os.path.exists(fname):
        raise BufrTableError(_text_file_not_found % fname)
    with open(fname, "rb") as fh:
        for line in fh:
            if line.startswith('#') or len(line) < 3:
                continue
            e = None
            el = line.rstrip().split('\t')
            #  0          1            2         3            4                 5                    6
            # "FXY<tab>libDWDType<tab>unit<tab>scale<tab>referenceValue<tab>dataWidth_Bits<tab>descriptor_name<lf>"
            # descr, typ, unit, abbrev, full_name, scale, refval, width
            e = TabBelem(int(el[0]), el[1], el[2], None, el[6], int(el[3]), int(el[4]), int(el[5]))
            tables.tab_b[int(el[0])] = e
    return True

def load_tab_c(tables, fname):
    """Load table C (operators) from 'fname' into object Tables."""
    if not os.path.exists(fname):
        raise BufrTableError(_text_file_not_found % fname)
    with open(fname, "rb") as fh:
        for line in fh:
            if line.startswith('#') or len(line) < 3:
                continue
            d = None
            e = None
            el = line.rstrip().split(',')
            #   0       1      2                3
            # Edition, FXY, OperatorName_en, OperationDefinition_en
            d = el[1]
            e = (el[2], el[3])
            if d.endswith("YYY"):
                tables.tab_c[int(d[0:3])] = e
            else:
                tables.tab_c[int(d)] = e
    return True

def load_tab_d(tables, fname):
    """Load table D (sequences) from 'fname' into object Tables."""
    if not os.path.exists(fname):
        raise BufrTableError(_text_file_not_found % fname)
    with open(fname, "rb") as fh:
        desc = None
        e = []
        for line in fh:
            if line.startswith('#') or len(line) < 3:
                continue
            try:
                le = line.split('\t')
                if len(le[0]):
                    if len(e):
                        tables.tab_d[int(desc)] = tuple(e)
                        e = []
                    desc = le[0]
                e.append(int(le[-1]))
            except BaseException as e:
                raise BufrTableError(e)
    return True

def load_tab_cf(tables, fname):
    """
    Load table E (code- and flagtables) into object Tables.
    fname is a directory for ecCodes, a file for libDWD.
    """
    if not os.path.exists(fname):
        raise BufrTableError(_text_file_not_found % fname)
    with open(fname, "rb") as fh:
        for line in fh:
            if line.startswith('#') or len(line) < 3:
                continue
            e = line.rstrip().split('\t')
            if e[4].startswith("Reserved") or e[4].startswith("Not used"):
                continue
            try:
                if e[3] == 'A':
                    v = -1
                else:
                    v = int(e[2])
                tables.tab_cf.setdefault(int(e[0]), {})[int(v)] = e[4]
            except BaseException as e:
                logger.warn("Table parse error: ", e)
                raise BufrTableError(e)
    return True

def get_file(tabnum, base_path, master, center, subcenter, master_vers, local_vers):
    mp = os.path.join(base_path, "libDWD")
    lp = os.path.join(base_path, "libDWD", "local_%05d_%05d" % (center, subcenter))
    if '%' in _table_file_names[tabnum]:
        m = os.path.join(mp, _table_file_names[tabnum] % (master_vers))
        l = os.path.join(lp, _table_file_names[tabnum] % (local_vers))
    else:
        m = os.path.join(mp, _table_file_names[tabnum])
        l = os.path.join(lp, _table_file_names[tabnum])
    return (m, l)

