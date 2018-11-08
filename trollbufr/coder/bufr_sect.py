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
Functions decoding the sections 0-5 for all the meta-bin_data.
No bin_data json_data from section 4 are decoded.

Created on Nov 18, 2016
Ported to Py3  09/2018

@author: amaul
'''
from .errors import SUPPORTED_BUFR_EDITION, BufrEncodeError
from .functions import str2dtg, dtg2str

"""
Section 0
=========
0-3    "BUFR"
4-6    Total length
7      BUFR-edition
"""


def decode_sect0(bin_data, offset):
    """
    :return: offset, length, {size, edition}
    """
    keys = ["bufr", "size", "edition"]
    vals = bin_data.readlist("bytes:4, uintbe:24, uint:8")
    if vals[0] != b"BUFR":
        return -1, -1, {}
    return bin_data.get_point(), 8, dict(list(zip(keys[1:], vals[1:])))


def encode_sect0(bin_data, edition=4):
    """
    :return: section start offset, meta-dict
    """
    # Originally:
    # bin_data.writelist("bytes:4={}, uintbe:24={}, uint:8={}", ("BUFR", 0, edition))
    # The next two lines are a workaround, since in Py3 bitstring seems to
    # evaluate "bytes:" incorrectly.
    bin_data.write_bytes("BUFR")
    bin_data.writelist("uintbe:24={}, uint:8={}", (0, edition))
    return 0, {"edition": edition}


def encode_bufr_size(bin_data):
    """Set total size of BUFR in size filed of section 0."""
    bin_data.set_uint(len(bin_data) // 8, 24, 32)


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


def decode_sect1(bin_data, offset, edition=4):
    """
    :return: offset, length, {master, center, subcenter, update, cat, cat_int, cat_loc, mver, lver, datetime, sect2}
    """
    key_offs = {
        3: (("length", "master", "subcenter", "center", "update", "sect2", "cat", "cat_loc", "mver", "lver", "datetime"),
            "uint:24, uint:8, uint:8, uint:8, uint:8, bool, pad:7, uint:8, uint:8, uint:8, uint:8, bytes:5"
            ),
        4: (("length", "master", "center", "subcenter", "update", "sect2", "cat", "cat_int", "cat_loc", "mver", "lver", "datetime"),
            "uint:24, uint:8, uint:16, uint:16, uint:8, bool, pad:7, uint:8, uint:8, uint:8, uint:8, uint:8, bytes:7"
            ),
    }
    vals = bin_data.readlist(key_offs[edition][1])
    rd = dict(list(zip(key_offs[edition][0], vals)))
    rd["datetime"] = str2dtg(rd["datetime"], ed=edition)
    l = rd.pop("length")
    if bin_data.get_point() < offset + l:
        rd["sect1_local_use"] = bin_data.readlist("hex:8," * (offset + l - bin_data.get_point()))
        if edition == 3 and rd["sect1_local_use"] == [b"00"]:
            rd.pop("sect1_local_use")
    bin_data.reset(offset + l)
    return offset + l, l, rd


def encode_sect1(bin_data, json_data, edition=4):
    """
    :param json_data: list or tuple with slots
        (master, center, subcenter, update, sect2, cat, cat_int, cat_loc, mver, lver,
        str2dtg-yy, str2dtg-mo, str2dtg-dy, str2dtg-hh, str2dtg-mi, str2dtg-ss)
    :return: section start offset, meta-dict
    """
    key_offs = {3: (("master", "subcenter", "center",
                     "update", "sect2",
                     "cat", "cat_loc",
                     "mver", "lver"),
                    "uint:24=0, uint:8={}, uint:8={}, uint:8={},"
                    + "uint:8={}, bool={}, pad:7, "
                    + "uint:8={}, uint:8={}, "
                    + "uint:8={}, uint:8={}"
                    ),
                4: (("master", "center", "subcenter",
                     "update", "sect2",
                     "cat", "cat_int", "cat_loc",
                     "mver", "lver"),
                    "uint:24=0, uint:8={}, uint:16={}, uint:16={}, "
                    + "uint:8={}, bool={}, pad:7, "
                    + "uint:8={}, uint:8={}, uint:8={}, "
                    + "uint:8={}, uint:8={}"
                    )
                }
    loc_use = None
    if isinstance(json_data, dict):
        if "sect1_local_use" in json_data:
            loc_use = json_data.pop("sect1_local_use")
        ord_val = [json_data[k] for k in key_offs[edition][0]]
        rd = json_data
        rd["datetime"] = dtg2str(json_data["datetime"], edition)
    else:
        if isinstance(json_data[-1], (list, tuple)):
            loc_use = json_data[-1]
            json_data = json_data[:-1]
        ord_val = json_data
        rd = dict(list(zip(key_offs[edition][0], json_data[:-6])))
        rd["datetime"] = dtg2str(json_data[-6:], edition)
    section_start = len(bin_data)
    bin_data.writelist(key_offs[edition][1], ord_val)
    if edition == 3:
        bin_data.write_bytes(rd["datetime"], 5 * 8)
    else:
        bin_data.write_bytes(rd["datetime"], 7 * 8)
    if loc_use:
        bin_data.writelist("hex:8={}," * len(loc_use), loc_use)
    (edition == 3) and bin_data.write_align(True)
    rd["length"] = (len(bin_data) - section_start) // 8
    bin_data.set_uint(rd["length"], 24, section_start)
    return section_start // 8, rd


"""
Section 2
=========
0-2   Section length
3     Reserved
4-n   Local data
"""


def decode_sect2(bin_data, offset):
    """
    :return: offset, length, {}
    """
    l = bin_data.readlist("uint:24, pad:8")[0]
    s2data = bin_data.readlist("hex:8," * (l - 4))
    bin_data.reset(offset + l)
    return offset + l, l, {"data_start": offset + 4, "data_end": offset + l, "sect2_data": s2data}


def encode_sect2(bin_data, json_data):
    """
    :return: section start offset
    """
    section_start = len(bin_data)
    bin_data.writelist("uint:24={}, pad:8", (0,))
    bin_data.writelist("hex:8={}," * len(json_data), json_data)
    sz = (len(bin_data) - section_start) // 8
    bin_data.set_uint(sz, 24, section_start)
    return section_start // 8


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


def decode_sect3(bin_data, offset):
    """
    Use {}[desc] for bin_data-iterator iter_data().

    :return: offset, length, {subsets, obs, comp, desc}
    """
    keys = ("length", "subsets", "obs", "comp")
    vals = bin_data.readlist("uint:24, pad:8, uint:16, bool, bool, pad:6")
    rd = dict(list(zip(keys, vals)))
    l = rd.pop("length")
    desc = []
    while bin_data.get_point() < offset + l - 1:
        df, dx, dy = bin_data.readlist("uint:2, uint:6, uint:8")
        desc.append(int("%d%02d%03d" % (df, dx, dy)))
    rd["descr"] = desc
    bin_data.reset(offset + l)
    return offset + l, l, rd


def encode_sect3(bin_data, json_data, edition=4):
    """
    :param json_data: list or tuple with slots (subsets, obs, comp)
    :return: section start offset, meta-dict
    """
    if edition not in SUPPORTED_BUFR_EDITION:
        raise BufrEncodeError()
    section_start = len(bin_data)
    bin_data.writelist("uint:24=0, pad:8, uint:16={}, bool={}, bool={}, pad:6", (json_data[:3]))
    descr = []
    rd = {"subsets": json_data[0], "obs": json_data[1], "comp": json_data[2]}
    for d in json_data[3]:
        bin_data.writelist("uint:2={}, uint:6={}, uint:8={}", (int(d[0:1]), int(d[1:3]), int(d[3:])))
        descr.append(int(d))
    # Ed.3: pad section to even number of octets.
    bin_data.write_align(edition == 3)
    rd["descr"] = descr
    sz = (len(bin_data) - section_start) // 8
    bin_data.set_uint(sz, 24, section_start)
    return section_start // 8, rd


"""
Section 4
=========
0-2   Section length
3     Reserved
4-n   Data
"""


def decode_sect4(bin_data, offset):
    """
    :return: offset, length, {data_start, data_end}
    """
    l = bin_data.read("uint:24")
    bin_data.reset(offset + l)
    return offset + l, l, {"data_start": offset + 4, "data_end": offset + l}


def encode_sect4(bin_data, edition=4):
    """
    :return: section start offset
    """
    if edition not in SUPPORTED_BUFR_EDITION:
        raise BufrEncodeError()
    section_start = len(bin_data)
    bin_data.writelist("uint:24={}, pad:8", (0,))
    return section_start // 8


def encode_sect4_size(bin_data, section_start, section_end):
    """Set size of BUFR bin_data section in size field of section 4."""
    bin_data.set_uint((section_end - section_start), 24, section_start * 8)


"""
Section 5
=========
0-3   "7777"
"""


def decode_sect5(bin_data, offset):
    """
    :return: offset, length, {}
    """
    if bin_data.read("bytes:4") == b"7777":
        return offset + 4, 4, {}
    else:
        return -1, -1, {}


def encode_sect5(bin_data):
    """
    :return: section start offset
    """
    section_start = len(bin_data)
    bin_data.write_bytes(b"7777")
    return section_start // 8
