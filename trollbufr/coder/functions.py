#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2016-2018 Alexander Maul
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
Collection of functions handling bits and bytes.

Created on Oct 28, 2016

@author: amaul
'''

import datetime
import logging
import struct
from errors import BufrDecodeError
from tables import TabBelem

logger = logging.getLogger("trollbufr")

from collections import namedtuple
DescrDataEntry = namedtuple("DescrDataEntry", "descr mark value quality")


def str2num(octets):
    """Convert all characters from octets (high->low) to int"""
    v = 0
    i = len(octets) - 1
    for b in octets:
        v |= ord(b) << 8 * i
        i -= 1
    return v


def octets2num(data, offset, count):
    """Convert character slice of length count from data (high->low) to int.

    Returns offset+count, the character after the converted characters, and the integer value.

    :return: offset,value
    """
    v = 0
    i = count - 1
    for b in data[offset: offset + count]:
        v |= ord(b) << 8 * i
        i -= 1
    return offset + count, v


def get_rval(data, comp, subs_num, tab_b_elem=None, alter=None, fix_width=None):
    """Read a raw value integer from the data section.

    The number of bits are either fixed or determined from Tab.B and previous alteration operators.
    Compression is taken into account.

    :return: raw value integer
    """
    if fix_width is not None:
        loc_width = fix_width
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("OCTETS       : FXW w+a:_+_ fw:%d qual:_ bc:%d #%d",  # ->ord(%02X)",
                         fix_width, data.bc, data.p,  # ord(data[data.p])
                         )
    elif tab_b_elem is not None and (31000 <= tab_b_elem.descr < 32000):
        # replication/repetition descriptor (group 31) is never altered.
        loc_width = tab_b_elem.width
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("OCTETS %06d: NAL w+a:_+_ fw:_ qual:_ bc:%d #%d->ord(%02X)",
                         tab_b_elem.descr, data.bc, data.p, ord(data[data.p])
                         )
    elif tab_b_elem is not None and alter is not None:
        if tab_b_elem.typ == TabBelem.STRING and alter.wchr:
            loc_width = alter.wchr
        elif tab_b_elem.typ == TabBelem.DOUBLE or tab_b_elem.typ == TabBelem.LONG:
            if alter.ieee:
                loc_width = alter.ieee
            else:
                loc_width = tab_b_elem.width + alter.wnum
        else:
            loc_width = tab_b_elem.width
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("OCTETS %06d:     w+a:%d%+d fw:_ qual:%d bc:%d  #%d",  # ->ord(%02X)",
                         tab_b_elem.descr, tab_b_elem.width, alter.wnum, alter.assoc[-1],
                         data.bc, data.p,  # ord(data[data.p])
                         )
    else:
        raise BufrDecodeError("Can't determine width.")
    if comp:
        return cset2octets(data, loc_width, subs_num, tab_b_elem.typ if tab_b_elem is not None else TabBelem.LONG)
    else:
        return data.read_bits(loc_width)


def cset2octets(data, loc_width, subs_num, btyp):
    """Like Blob.read_bits(), but for compressed data.

    :return: octets
    """
    min_val = data.read_bits(loc_width)
    cwidth = data.read_bits(6)
    if btyp == TabBelem.STRING:
        cwidth *= 8
    if cwidth == 0 or min_val == all_one(loc_width):
        # All equal or all missing
        v = min_val
    else:
        # Data compressed
        logger.debug("CSET loc_width %d  subnum %s  cwidth %d", loc_width, subs_num, cwidth)
        data.read_skip(cwidth * subs_num[0])
        n = data.read_bits(cwidth)
        if n == all_one(cwidth):
            n = all_one(loc_width)
        v = min_val + n
        data.read_skip(cwidth * (subs_num[1] - subs_num[0] - 1))
    return v


def rval2str(rval):
    """Each byte of the integer rval is taken as a character, they are joined into a string"""
    octets = []
    while rval:
        if rval & 0xFF >= 0x20:
            octets.append(chr(rval & 0xFF))
        rval >>= 8
    octets.reverse()
    val = "".join(octets)
    return val


def rval2num(tab_b_elem, alter, rval):
    """Return bit-sequence rval as a value.

    Return the numeric value for all bits in rval decoded with descriptor descr,
    or type str if tab_b_elem describes a string.
    If the value was interpreted as "missing", None is returned.

    type(value):
    * numeric: int, float
    * codetable/flags: int
    * IA5 characters: string

    :return: value

    :raise: KeyError if descr is not in table.
    """
    # Default return value is "missing value"
    val = None
    # The "missing-value" bit-masks for IEEE float/double
    _IEEE32_INF = 0x7f7fffff
    _IEEE64_INF = 0x7fefffffffffffff

    # Alter = {'wnum':0, 'wchr':0, 'refval':0, 'scale':0, 'assoc':0}
    if tab_b_elem.typ == TabBelem.STRING and alter.wchr:
        loc_width = alter.wchr
    else:
        loc_width = tab_b_elem.width + alter.wnum
    loc_refval = alter.refval.get(tab_b_elem.descr, tab_b_elem.refval * alter.refmul)
    loc_scale = tab_b_elem.scale + alter.scale

    logger.debug("EVAL %06d: typ:%s width:%d ref:%d scal:%d%+d",
                 tab_b_elem.descr, tab_b_elem.typ, loc_width, loc_refval, tab_b_elem.scale, alter.scale)

    if rval == all_one(loc_width) and (tab_b_elem.descr < 31000 or tab_b_elem.descr >= 31020):
        # First, test if all bits are set, which usually means "missing value".
        # The delayed replication and repetition descr are special nut-cases.
        logger.debug("rval %d ==_(1<<%d)%d    #%06d/%d", rval, loc_width,
                     all_one(loc_width), tab_b_elem.descr, tab_b_elem.descr / 1000)
        val = None
    elif alter.ieee and (tab_b_elem.typ == TabBelem.DOUBLE or tab_b_elem.typ == TabBelem.LONG):
        # IEEE 32b or 64b floating point number, INF means "missing value".
        if alter.ieee != 32 and alter.ieee != 64:
            raise BufrDecodeError("Invalid IEEE size %d" % alter.ieee)
        if alter.ieee == 32 and not rval ^ _IEEE32_INF:
            val = struct.unpack("f", rval)
        elif alter.ieee == 64 and not rval ^ _IEEE64_INF:
            val = struct.unpack("d", rval)
        else:
            val = None
    elif tab_b_elem.typ == TabBelem.DOUBLE or loc_scale > 0:
        # Float/double: add reference, divide by scale
        val = float(rval + loc_refval) / 10 ** loc_scale
    elif tab_b_elem.typ == TabBelem.LONG:
        # Integer: add reference, divide by scale
        val = (rval + loc_refval) / 10 ** loc_scale
    elif tab_b_elem.typ == TabBelem.STRING:
        # For string, all bytes are reversed.
        val = rval2str(rval)
    else:
        val = rval

    logger.debug("DECODE %06d: (%d) -> \"%s\"", tab_b_elem.descr, rval, str(val))

    return val


def all_one(x):
    """Set all bits of width x to '1'."""
    return (1 << x) - 1


def b2s(n):
    """Builds a string with characters 0 and 1, representing the bits of an integer n."""
    a = 2 if n // 256 else 1
    m = 1 << 8 * a - 1
    return "".join([('1' if n & (m >> i) else '0') for i in range(0, 8 * a)])


def dtg(octets, ed=4):
    """Interpret octet sequence as datetime object.

    Ed.3: year [yy], month, day, hour, minute
    Ed.4: year [yyyy], month, day, hour, minute, second
    """
    if ed == 3:
        o, yy = octets2num(octets, 0, 1)
    elif ed == 4:
        o, yy = octets2num(octets, 0, 2)
    o, mo = octets2num(octets, o, 1)
    o, dy = octets2num(octets, o, 1)
    o, hr = octets2num(octets, o, 1)
    o, mi = octets2num(octets, o, 1)
    if ed == 3:
        if yy > 50:
            yy += 1900
        else:
            yy += 2000
        sc = 0
    elif ed == 4:
        o, sc = octets2num(octets, o, 1)
    return datetime.datetime(yy, mo, dy, hr, mi, sc)


def descr_is_nil(desc):
    """True if descriptor is null."""
    return desc == 0


def descr_is_data(desc):
    """True if descriptor is Tab-B data descriptor."""
    return 0 < desc < 100000


def descr_is_loop(desc):
    """True if descriptor is replication/repetition."""
    return 100000 <= desc < 200000


def descr_is_oper(desc):
    """True if descriptor is operator."""
    return 200000 <= desc < 300000


def descr_is_seq(desc):
    """True if descriptor is sequence."""
    return 300000 <= desc < 400000

# Yet not existent.
# def descr_is_dseq(desc):
#     """True if descriptor is delayed sequence (Ed.5)."""
#     return 400000 <= desc < 500000


def get_descr_list(tables, desc3):
    """List all expanded descriptors."""
    desc_list = []
    stack = [(desc3, 0)]
    while stack:
        dl, di = stack.pop()
        while di < len(dl):
            if descr_is_nil(dl[di]):
                di += 1
            elif descr_is_data(dl[di]) or descr_is_loop(dl[di]) or descr_is_oper(dl[di]):
                desc_list.append(dl[di])
                di += 1
            elif descr_is_seq(dl[di]):
                desc_list.append(dl[di])
                stack.append((dl, di + 1))
                dl = tables.tab_d[dl[di]]
                di = 0
    return desc_list
