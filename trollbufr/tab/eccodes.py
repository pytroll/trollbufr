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

import glob
import logging
import os
import re

from errors import BufrTableError
from tables import TabBelem

logger = logging.getLogger("trollbufr")

"""
##### Description of recognized table format =eccodes= #####

----- path/file -----
./MasterTable/"wmo"/MasterVersion
./MasterTable/"local"/LocalVersion/Centre/SubCentre
    codetables/XY.table
    element.table
    sequence.def

----- codetable -----
N N Value

----- element.table -----
   0      1         2    3    4     5       6       7      8          9         10
#code|abbreviation|type|name|unit|scale|reference|width|crex_unit|crex_scale|crex_width
000001|tableAEntry|string|TABLE A: ENTRY|CCITT IA5|0|0|24|Character|0|3

----- sequence.def -----
"300002" = [  000002, 000003 ]

----- operators.table -----
#code|abbreviation|type|name|unit|scale|reference|width|crex_unit|crex_scale|crex_width
222000|qualityInformationFollows|long|The values of class 33 elements which follow relate to the data defined by the data present bit-map|OPERATOR|0|0|0|0|0|

----- common code tables -----
#code|meaning
0|Surface data - land

############################################################
"""

_table_file_names = {
    "A": "../../../datacat.table",
    "B": "element.table",
    "C": "../../../operators.table",
    "D": "sequence.def",
    "CF": "codetables",
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
            el = line.rstrip().split('|')
            #  0       1         2    3    4     5       6       7      8          9         10
            # code|abbreviation|type|name|unit|scale|reference|width|crex_unit|crex_scale|crex_width
            # descr, typ, unit, abbrev, full_name, scale, refval, width
            if el[2] == "table":
                t = el[4].lower()
                if "code table" in t:
                    t = "code"
                elif "flag table" in t:
                    t = "flag"
            else:
                t = el[2]
            e = TabBelem(int(el[0]), t, el[4], el[1], el[3], int(el[5]), int(el[6]), int(el[7]))
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
            el = line.rstrip().split('|')
            #  0       1         2    3    4     5       6       7      8          9         10
            # code|abbreviation|type|name|unit|scale|reference|width|crex_unit|crex_scale|crex_width
            #  y     y           n    y    n...
            d = el[0]
            e = (el[1], el[3])
            if d.endswith("YYY"):
                tables.tab_c[int(d[0:3])] = e
            else:
                tables.tab_c[int(d)] = e
    return True

def load_tab_d(tables, fname):
    """Load table D (sequences) from 'fname' into object Tables."""
    if not os.path.exists(fname):
        raise BufrTableError(_text_file_not_found % fname)
    # Using regex for eccodes' sequence.tab, for libdwd we split on tabulator.
    re_fl = re.compile("\"(?P<desc>\d+)\"\s*=\s*\[(?P<exp>[0-9, ]+)\]")
    with open(fname, "rb") as fh:
        desc = None
        e = []
        cline = ""
        for line in fh:
            if line.startswith('#') or len(line) < 3:
                continue
            # Some eccodes' sequence.tab have newline inside a sequence-array,
            # we can assume this happens when matcher m is None.
            # To handle that case cline is a buffer collecting lines until
            # cline matches the regex re_fl.
            cline += line.strip()
            m = re_fl.match(cline)
            if m is None:
                continue
            desc = m.group('desc')
            ll = m.group('exp').split(',')
            e = []
            for le in ll:
                e.append(int(le))
            tables.tab_d[int(desc)] = tuple(e)
            cline = ""
    return True

def load_tab_cf(tables, fname):
    """
    Load table E (code- and flagtables) into object Tables.
    fname is a directory for ecCodes, a file for libDWD.
    """
    if not os.path.exists(fname):
        raise BufrTableError(_text_file_not_found % fname)
    for fn_etab in glob.glob(os.path.join(fname, "*.table")):
        desc = os.path.basename(fn_etab).split('.')
        with open(fn_etab, "rb") as fh:
            for line in fh:
                if line.startswith('#') or len(line) < 3:
                    continue
                try:
                    e = line.rstrip().split(' ', 2)
                    if e[2].startswith("Reserved") or e[2].startswith("Not used"):
                        continue
                    tables.tab_cf.setdefault(int(desc[0]), {})[int(e[0])] = e[2].replace("\"    ", "")
                except IndexError:
                    logger.warn("Table parse: no values: '%s' in '%s'", line.strip(), fn_etab)
    return True

def get_file(tabnum, base_path, master, center, subcenter, master_vers, local_vers):
    mp = os.path.join(base_path, "bufr", "tables", str(master), "wmo", str(master_vers))
    lp = os.path.join(base_path, "bufr", "tables", str(master), "local", str(local_vers), str(center), str(subcenter))
    if '%' in _table_file_names[tabnum]:
        m = os.path.join(mp, _table_file_names[tabnum] % (master_vers))
        l = os.path.join(lp, _table_file_names[tabnum] % (local_vers))
    else:
        m = os.path.join(mp, _table_file_names[tabnum])
        l = os.path.join(lp, _table_file_names[tabnum])
    return (m, l)

