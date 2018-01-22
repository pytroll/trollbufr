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
from errors import BufrDecodeError

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
    o = offset
    if data[o:o + 4] != "BUFR":
        return -1, {}
    o += 4
    o, l = f.octets2num(data, o, 3)
    o, e = f.octets2num(data, o, 1)
    return o, 8, {'size':l, 'edition':e}

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
                3:(("length", 0, 2), ("master", 3, 3), ("center", 5, 5), ("subcenter", 4 , 4),
                   ("update", 6, 6), ("cat", 8, 8), ("cat_int", 9, 9), ("cat_loc", 9, 9),
                   ("mver", 10, 10), ("lver", 11, 11), ("datetime", 12 , 16), ("sect2", 7, 7),
                ),
                4:(("length", 0, 2), ("master", 3, 3), ("center", 4, 5), ("subcenter", 6 , 7),
                   ("update", 8, 8), ("cat", 10, 10), ("cat_int", 11, 11), ("cat_loc", 12, 12),
                   ("mver", 13, 13), ("lver", 14, 14), ("datetime", 15 , 21), ("sect2", 9, 9),
                ),
            }
    rd = {}
    for t in key_offs[edition]:
        if t[1] is None:
            rd[t[0]] = None
        elif t[0] == "datetime":
            rd[t[0]] = f.dtg(data[offset + t[1]:offset + t[2] + 1], edition)
        else:
            _, rd[t[0]] = f.octets2num(data, offset + t[1], t[2] - t[1] + 1)
    rd['sect2'] = rd['sect2'] & 128
    l = int(rd.pop('length'))
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
    _, l = f.octets2num(data, offset, 3)
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
    rd = {}
    o, l = f.octets2num(data, offset, 3)
    if offset + l >= len(data):
        raise BufrDecodeError("SECT_3: invalid length (%d > %d)" % (offset + l, len(data)))
    o += 1 # reserved octet
    o, rd['subsets'] = f.octets2num(data, o, 2)
    o, fl = f.octets2num(data, o, 1)
    rd['obs'] = True if fl & 128 else False
    rd['comp'] = True if fl & 64 else False
    desc = []
    while o < offset + l - 1:
        df = ord(data[o]) >> 6
        dx = ord(data[o]) & 63
        o += 1
        dy = ord(data[o])
        desc.append(int("%d%02d%03d" % (df, dx, dy)))
        o += 1
    rd['descr'] = desc
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
    o, l = f.octets2num(data, offset, 3)
    return offset + l, l, { 'data_start':o + 1, 'data_end':offset + l}

"""
Section 5
=========
0-3   "7777"
"""
def decode_sect5(data, offset):
    """
    RETURN offset, length, {}
    """
    if data[offset:offset + 4] == "7777":
        return offset + 4, 4, {}
    else:
        return -1, -1, {}


