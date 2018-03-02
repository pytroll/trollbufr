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
Functions decoding the sections 0-5 for all the meta-data.
No data values from section 4 are decoded.

Created on Nov 18, 2016

@author: amaul
'''
import logging
logger = logging.getLogger("trollbufr")
import functions as f

"""
Section 0
=========
0-3    "BUFR"
4-6    Total length
7      BUFR-edition
"""


def decode_sect0(data, offset):
    """
    RETURN offset, length, {size, edition}
    """
    keys = ["bufr", "size", "edition"]
    vals = data.readlist("bytes:4, uintbe:24, uint:8")
    if vals[0] != "BUFR":
        return -1, {}
    return data.get_point(), 8, dict(zip(keys[1:], vals[1:]))


"""
Section 1
=========
BUFR Vers. 3
-----------
0-2   Section length
3     Master table
4     Sub-centre
5     Centre
6     Update sequence number (0 = original, 1.. = updates)
7     Flag: 00 = no sect2, 01 = sect2 present, 02-ff = reserved
8     Data category
9     Sub-category
10    Master table version
11    Local table version
12    Year [yy]
13    Month
14    Day
15    Hour
16    Minute
17-n  Reserved

BUFR Vers. 4
------------
0-2   Section length
3     Master table
4-5   Centre
6-7   Sub-centre
8     Update sequence number (0 = original, 1.. = updates)
9     Flag, 0x00 = no sect2, 0x01 = sect2 present, 0x02-0xff = reserved
10    Data-category
11    Internat. sub-category
12    Local sub-category
13    Master table version
14    Local table version
15-16 Year [yyyy]
17    Month
18    Day
19    Hour
20    Minute
21    Second
(22-n Reserved)
"""


def decode_sect1(data, offset, edition=4):
    """
    RETURN offset, length, {master, center, subcenter, update, cat, cat_int, cat_loc, mver, lver, datetime, sect2}
    """
    key_offs = {
        3: (("length", "master", "subcenter", "center", "update", "sect2", "cat", "cat_loc", "mver", "lver", "datetime"),
            "uint:24, uint:8, uint:8, uint:8, uint:8, bool, pad:7, uint:8, uint:8, uint:8, uint:8, bytes:5"
            ),
        4: (("length", "master", "center", "subcenter", "update", "sect2", "cat", "cat_int", "cat_loc", "mver", "lver", "datetime"),
            "uint:24, uint:8, uint:16, uint:16, uint:8, bool, pad:7, uint:8, uint:8, uint:8, uint:8, uint:8, bytes:9"
            ),
    }
    vals = data.readlist(key_offs[edition][1])
    rd = dict(zip(key_offs[edition][0], vals))
    rd["datetime"] = f.dtg(rd["datetime"], ed=edition)
    l = rd.pop("length")
    data.reset(offset + l)
    return offset + l, l, rd


"""
Section 2
=========
0-2   Section length
3     Reserved
4-n   Local data
"""


def decode_sect2(data, offset):
    """
    RETURN offset, length, {}
    """
    l = data.read("uint:24")
    data.reset(offset + l)
    return offset + l, l, {}


"""
Section 3
=========
0-2   Section length
3     Reserved
4-5   Number of subsets
6     Flag: &128 = other|observation, &64 = not compressed|compressed
7-n   List of descriptors
        FXXYYY: F = 2bit, & 0xC000 ; XX = 6bit, & 0x3F00 ; YYY = 8bit, & 0xFF
        F=0: element/Tab.B, F=1: repetition, F=2: operator/Tab.C, F=3: sequence/Tab.D
"""


def decode_sect3(data, offset):
    """
    Use {}[desc] for data-iterator iter_data().

    RETURN offset, length, {subsets, obs, comp, desc}
    """
    keys = ("length", "subsets", "obs", "comp")
    vals = data.readlist("uint:24, pad:8, uint:16, bool, bool, pad:6")
    rd = dict(zip(keys, vals))
    l = rd.pop("length")
    desc = []
    while data.get_point() < offset + l - 1:
        df, dx, dy = data.readlist("uint:2, uint:6, uint:8")
        desc.append(int("%d%02d%03d" % (df, dx, dy)))
    rd['descr'] = desc
    data.reset(offset + l)
    return offset + l, l, rd


"""
Section 4
=========
0-2   Section length
3     Reserved
4-n   Data
"""


def decode_sect4(data, offset):
    """
    RETURN offset, length, {data_start, data_end}
    """
    l = data.read("uint:24")
    data.reset(offset + l)
    return offset + l, l, {'data_start': offset + 4, 'data_end': offset + l}


"""
Section 5
=========
0-3   "7777"
"""


def decode_sect5(data, offset):
    """
    RETURN offset, length, {}
    """
    if data.read("bytes:4") == "7777":
        return offset + 4, 4, {}
    else:
        return -1, -1, {}
