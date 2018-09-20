#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2016-2018 Alexander Maul
#
# Ported to Py3  09/2018
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
"""
Collection of functions handling bits and bytes.

Created on Oct 28, 2016

@author: amaul
"""

import datetime
import logging
import struct
from .errors import BufrDecodeError, BufrEncodeError, BufrTableError
from .bufr_types import AlterState, TabBType

logger = logging.getLogger("trollbufr")


def octets2num(bin_data, offset, count):
    """Convert character slice of length count from bin_data (high->low) to int.

    Returns offset+count, the character after the converted characters,
    and the integer value.

    :return: offset,value
    """
    v = 0
    i = count - 1
    for b in bin_data[offset: offset + count]:
        v |= b << 8 * i
        i -= 1
    return offset + count, v


def calc_width(bin_data, tab_b_elem=None, alter=None, fix_width=None, fix_typ=None):
    """Read a raw value integer from the data section.

    The number of bits are either fixed or determined from Tab.B and previous
    alteration operators.
    Compression is taken into account.

    :return: raw value integer
    """
    loc_typ = tab_b_elem.typ if tab_b_elem is not None else fix_typ
    if fix_width is not None:
        loc_width = fix_width
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("OCTETS       : FXW w+a:_+_ fw:%d qual:_ bc:%d #%d",  # ->ord(%02X)",
                         fix_width, bin_data.bc, bin_data.p,  # ord(bin_data[bin_data.p])
                         )
    elif tab_b_elem is not None and (31000 <= tab_b_elem.descr < 32000):
        # replication/repetition descriptor (group 31) is never altered.
        loc_width = tab_b_elem.width
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("OCTETS %06d: NAL w+a:_+_ fw:_ qual:_ bc:%d #%d",  # ->ord(%02X)",
                         tab_b_elem.descr, bin_data.bc, bin_data.p,  # ord(bin_data[bin_data.p])
                         )
    elif tab_b_elem is not None and alter is not None:
        if loc_typ == TabBType.STRING and alter.wchr:
            loc_width = alter.wchr
        elif loc_typ in (TabBType.DOUBLE, TabBType.LONG):
            if alter.ieee:
                loc_width = alter.ieee
            else:
                loc_width = tab_b_elem.width + alter.wnum
        else:
            loc_width = tab_b_elem.width
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("OCTETS %06d:     w+a:%d%+d fw:_ qual:%d bc:%d  #%d",  # ->ord(%02X)",
                         tab_b_elem.descr, tab_b_elem.width, alter.wnum, alter.assoc[-1],
                         bin_data.bc, bin_data.p,  # ord(bin_data[bin_data.p])
                         )
    else:
        raise BufrDecodeError("Can't determine width.")
    return loc_width, loc_typ


def get_val(bin_data, subs_num, tab_b_elem=None, alter=None, fix_width=None, fix_typ=None):
    loc_width, loc_typ = calc_width(bin_data, tab_b_elem, alter, fix_width, fix_typ)
    rval = bin_data.read_bits(loc_width)
    if fix_width is not None:
        if loc_typ == TabBType.STRING:
            return rval2str(rval)
        else:
            return rval
    else:
        return rval2num(tab_b_elem, alter, rval)


def get_val_comp(bin_data, subs_num, tab_b_elem=None, alter=None, fix_width=None, fix_typ=None):
    loc_width, loc_typ = calc_width(bin_data, tab_b_elem, alter, fix_width, fix_typ)
    rval = cset2octets(bin_data,
                       loc_width,
                       subs_num,
                       loc_typ or TabBType.LONG)
    if fix_width is not None:
        if loc_typ == TabBType.STRING:
            return rval2str(rval)
        else:
            return rval
    else:
        return rval2num(tab_b_elem, alter, rval)


def get_val_array(bin_data, subs_num, tab_b_elem=None, alter=None, fix_width=None, fix_typ=None):
    loc_width, loc_typ = calc_width(bin_data, tab_b_elem, alter, fix_width, fix_typ)
    rval_ary = cset2array(bin_data,
                          loc_width,
                          subs_num[1],
                          loc_typ or TabBType.LONG)
    if fix_width is None:
        rval_ary = [rval2num(tab_b_elem, alter, rval) for rval in rval_ary]
    elif loc_typ == TabBType.STRING:
        rval_ary = [rval2str(rval) for rval in rval_ary]
    return rval_ary


def cset2octets(bin_data, loc_width, subs_num, btyp):
    """Like Blob.read_bits(), but for compressed data.

    :return: octets
    """
    min_val = bin_data.read_bits(loc_width)
    cwidth = bin_data.read_bits(6)
    n = None
    v = None
    if btyp == TabBType.STRING:
        cwidth *= 8
    try:
        if cwidth == 0 or min_val == all_one(loc_width):
            # All equal or all missing
            v = min_val
        else:
            # Data compressed
            bin_data.read_skip(cwidth * subs_num[0])
            n = bin_data.read_bits(cwidth)
            if n == all_one(cwidth):
                v = all_one(loc_width)
            else:
                v = min_val + n
            bin_data.read_skip(cwidth * (subs_num[1] - subs_num[0] - 1))
    finally:
        logger.debug("CSET  subnum %s  loc_width %d  min_val %d  cwidth %d  cval %s  rval %d",
                     subs_num, loc_width, min_val, cwidth, n, v)
    return v


def cset2array(bin_data, loc_width, subs_cnt, btyp):
    """Like Blob.read_bits(), but for compressed data.

    :return: octets
    """
    min_val = bin_data.read_bits(loc_width)
    cwidth = bin_data.read_bits(6)
    single_val = None
    val_ary = [None] * subs_cnt
    if btyp == TabBType.STRING:
        cwidth *= 8
    try:
        if cwidth == 0 or min_val == all_one(loc_width):
            # All equal or all missing
            val_ary = [min_val] * subs_cnt
        else:
            # Data compressed
            for i in range(subs_cnt):
                single_val = bin_data.read_bits(cwidth)
                if single_val == all_one(cwidth):
                    val_ary[i] = all_one(loc_width)
                else:
                    val_ary[i] = min_val + single_val
    finally:
        logger.debug("CSET  subnum %s  loc_width %d  min_val %d  cwidth %d  cval %s  rval %s",
                     subs_cnt, loc_width, min_val, cwidth, single_val, val_ary)
    return val_ary


def rval2str(rval):
    """Each byte of the integer rval is taken as a character,
    they are joined into a string.
    """
    octets = []
    while rval:
        if rval & 0xFF >= 0x20:
            octets.append(chr(rval & 0xFF))
        rval >>= 8
    octets.reverse()
    val = "".join(octets)
    return val


_IEEE_INF = {32: ("f", 0x7f7fffff), 64: ("d", 0x7fefffffffffffff)}
"""The "missing-value" bit-masks for IEEE float/double."""


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

    # Alter = {'wnum':0, 'wchr':0, 'refval':0, 'scale':0, 'assoc':0}
    if tab_b_elem.typ == TabBType.CODE or tab_b_elem.typ == TabBType.FLAG:
        loc_width = tab_b_elem.width
        loc_refval = tab_b_elem.refval
        loc_scale = tab_b_elem.scale
    elif tab_b_elem.typ == TabBType.STRING:
        loc_width = alter.wchr or tab_b_elem.width
        loc_refval = tab_b_elem.refval
        loc_scale = tab_b_elem.scale
    else:
        loc_width = tab_b_elem.width + alter.wnum
        loc_refval = alter.refval.get(tab_b_elem.descr, tab_b_elem.refval * alter.refmul)
        loc_scale = tab_b_elem.scale + alter.scale
    if (rval == all_one(loc_width)
            and (tab_b_elem.descr < 31000 or tab_b_elem.descr >= 31020)):
        # First, test if all bits are set, which usually means "missing value".
        # The delayed replication and repetition descr are special nut-cases.
        logger.debug("rval %d ==_(1<<%d)%d    #%06d/%d", rval, loc_width,
                     all_one(loc_width), tab_b_elem.descr,
                     tab_b_elem.descr // 1000)
        val = None
    elif alter.ieee and (tab_b_elem.typ == TabBType.DOUBLE
                         or tab_b_elem.typ == TabBType.LONG):
        # IEEE 32b or 64b floating point number, INF means "missing value".
        if alter.ieee not in _IEEE_INF:
            raise BufrDecodeError("Invalid IEEE size %d" % alter.ieee)
        if not rval ^ _IEEE_INF[alter.ieee][1]:
            val = struct.unpack(_IEEE_INF[alter.ieee][0], rval)
        else:
            val = None
    elif tab_b_elem.typ == TabBType.DOUBLE or loc_scale > 0:
        # Float/double: add reference, divide by scale
        val = float(rval + loc_refval) / 10 ** loc_scale
    elif tab_b_elem.typ == TabBType.LONG:
        # Integer: add reference, divide by scale
        val = int((rval + loc_refval) / 10 ** loc_scale)
    elif tab_b_elem.typ == TabBType.STRING:
        val = rval2str(rval)
    else:
        val = rval

    logger.debug("EVAL-RV %06d: typ:%s width:%d ref:%d scal:%d%+d val:(%d)->(%s)",
                 tab_b_elem.descr, tab_b_elem.typ, loc_width, loc_refval,
                 tab_b_elem.scale, alter.scale, rval, str(val))

    return val


def num2rval(tab_b_elem, alter, value):
    """Create the bit-sequence for a value.

    Encode a numeric value for with descriptor descr, apply altering if provided.
    If the value is "missing", it's encoded as "all bits are set to 1".

    :return: raw value

    :raise: KeyError if descr is not in table.
    """
    if alter is None:
        # If alter is None, we make a new, empty object for default values.
        alter = AlterState()
    # Alter = {'wnum':0, 'wchr':0, 'refval':0, 'scale':0, 'assoc':0}
    if tab_b_elem.typ == TabBType.CODE or tab_b_elem.typ == TabBType.FLAG:
        loc_width = tab_b_elem.width
        loc_refval = tab_b_elem.refval
        loc_scale = tab_b_elem.scale
    elif tab_b_elem.typ == TabBType.STRING:
        loc_width = alter.wchr or tab_b_elem.width
        loc_refval = tab_b_elem.refval
        loc_scale = tab_b_elem.scale
        value = value.encode("latin1") if value is not None else value
    else:
        loc_width = tab_b_elem.width + alter.wnum
        loc_refval = alter.refval.get(tab_b_elem.descr, tab_b_elem.refval * alter.refmul)
        loc_scale = tab_b_elem.scale + alter.scale
    if value is None and (tab_b_elem.descr < 31000 or tab_b_elem.descr >= 31020):
        # First, for "missing value" set all bits to 1.
        # The delayed replication and repetition descr are special cases.
        if tab_b_elem.typ == TabBType.STRING:
            rval = b"\xff" * (loc_width // 8)
        else:
            rval = all_one(loc_width)
    elif alter.ieee and (tab_b_elem.typ == TabBType.DOUBLE or tab_b_elem.typ == TabBType.LONG):
        # IEEE 32b or 64b floating point number, INF means "missing value".
        if alter.ieee not in _IEEE_INF:
            raise BufrEncodeError("Invalid IEEE size %d" % alter.ieee)
        fmt = _IEEE_INF[alter.ieee][0]
        if value is None:
            value = _IEEE_INF[alter.ieee][1]
        rval = struct.pack(fmt, value)
    elif tab_b_elem.typ == TabBType.LONG or tab_b_elem.typ == TabBType.DOUBLE or loc_scale > 0:
        # Float/double/integer: add reference, divide by scale
        rval = int(round((value * 10 ** loc_scale) - loc_refval))
    else:
        rval = value

    logger.debug("EVAL-N  %06d: typ:%s width:%d>%d ref:%d scal:%d%+d val:(%s)->(%s)",
                 tab_b_elem.descr, tab_b_elem.typ, tab_b_elem.width, loc_width,
                 loc_refval, tab_b_elem.scale, alter.scale, value, str(rval))

    return rval, loc_width


def num2cval(tab_b_elem, alter, fix_width, value_list):
    """Process and compress a list of values and apply num2rval() to each.

    Returns the
    * uncompressed bit-width according the descriptor,
    * minimum value,
    * bit-width required for "value - minimum",
    * list of re-calculated values.

    :return:  loc_width, min_value, min_width, recal_val
    """
    rval_list = []
    if not any(True for x in value_list if x is not None) or max(value_list) == min(value_list):
        # All values are "missing", or all are equal
        if tab_b_elem and alter:
            min_value, loc_width = num2rval(tab_b_elem, alter, value_list[0])
        elif tab_b_elem and alter is None and fix_width is None:
            min_value, loc_width = value_list[0], tab_b_elem.width
        else:
            min_value, loc_width = value_list[0], fix_width
        min_width = 0
        recal_val = []
        recal_max_val = 0
    elif tab_b_elem is not None and tab_b_elem.typ == TabBType.STRING:
        for v in value_list:
            rval_list.extend(num2rval(tab_b_elem, alter, v))
        min_width = loc_width = rval_list[1]
        min_value = ""
        recal_max_val = -1
        recal_val = [(v if v != all_one(loc_width) else None)
                     for v in rval_list[::2]]
        recal_val = [(v if v is not None else all_one(min_width))
                     for v in recal_val]
    else:
        if tab_b_elem and alter:
            for v in value_list:
                rval_list.extend(num2rval(tab_b_elem, alter, v))
        else:
            for v in value_list:
                rval_list.extend((v, fix_width))
        loc_width = rval_list[1]
        min_value = min(rval_list[::2])
        min_width = 0
        recal_val = [(v - min_value if v != all_one(loc_width) else None)
                     for v in rval_list[::2]]
        recal_max_val = max(recal_val)
        min_width = recal_max_val.bit_length()
        if recal_max_val == all_one(min_width):
            min_width += 1
        recal_val = [(v if v is not None else all_one(min_width))
                     for v in recal_val]

    logger.debug("lw:%s  mval:%s  mwi:%s  max:%s  recal_vaL:%s", loc_width,
                 min_value, min_width, recal_max_val, recal_val)

    return loc_width, min_value, min_width, recal_val


def add_val(blob,  value_list, value_list_idx, tab_b_elem=None, alter=None, fix_width=None, fix_typ=None):
    """Append a value to the BUFR bitstream.

    Exactly one number or string is transformed with num2rval(), this is for
    not-compressed BUFR.

    :param blob: bitstream object.
    :param value_list: single value or value list, with latter index is required.
    :param value_list_idx: index to value_list, ignored if value_list is single value.
    :param tab_b_elem: descriptor
    :param alter: alteration object
    :param fix_width: fix bit-width, if descriptor is not applicable.
    :param fix_typ: fix type, if descriptor is not applicable.
    """
    if isinstance(value_list, (list, tuple)):
        val_buf = value_list[value_list_idx]
    else:
        # Take value_list as a simple value (e.g.: int), ignore value_list_idx.
        val_buf = value_list
    if fix_width is not None:
        loc_width = fix_width
        loc_value = val_buf
    elif tab_b_elem is not None and (31000 <= tab_b_elem.descr < 32000):
        # replication/repetition descriptor (group 31) is never altered.
        loc_width = tab_b_elem.width
        loc_value = val_buf
    elif tab_b_elem is not None and alter is not None:
        loc_value, loc_width = num2rval(tab_b_elem, alter, val_buf)
    else:
        raise BufrEncodeError("Can't determine width.")
    if loc_value is None:
        loc_value = all_one(loc_width)
    if (tab_b_elem is not None and tab_b_elem.typ == TabBType.STRING) or fix_typ == TabBType.STRING:
        blob.write_bytes(loc_value, loc_width)
    else:
        blob.write_uint(loc_value, loc_width)


def add_val_comp(blob, value_list, value_list_idx, tab_b_elem=None, alter=None, fix_width=None, fix_typ=None):
    """Append a set of values to a compressed BUFR bitstream.

    value_list_idx serves as index to value_list, or as multiplicator for a single value.

    :param blob: bitstream object.
    :param value_list: value list or single value, with latter index is required.
    :param value_list_idx: index to value_list, or number of subsets if value_list is single value.
    :param tab_b_elem: descriptor
    :param alter: alteration object
    :param fix_width: fix bit-width, if descriptor is not applicable.
    :param fix_typ: fix type, if descriptor is not applicable.
    """
    if tab_b_elem is None and fix_width is None:
        raise BufrEncodeError("Can't determine width.")
    val_l = mk_value_list(value_list, value_list_idx)
    if tab_b_elem is not None and (31000 <= tab_b_elem.descr < 32000):
        # Replication/repetition descriptor (group 31) is never altered.
        alter = None
    loc_width, min_value, min_width, recal_val = num2cval(tab_b_elem, alter, fix_width, val_l)
    if (tab_b_elem is not None and tab_b_elem.typ == TabBType.STRING) or fix_typ == TabBType.STRING:
        # Special handling for strings.
        blob.write_bytes(min_value, loc_width)
        blob.write_uint(min_width // 8, 6)
        for value in recal_val:
            blob.write_bytes(value, min_width)
    else:
        blob.write_uint(min_value, loc_width)
        blob.write_uint(min_width, 6)
        for value in recal_val:
            blob.write_uint(value, min_width)


def mk_value_list(value_list, value_list_idx):
    """Make a list of values from all subsets."""
    if isinstance(value_list, (list, tuple)):
        # Build a list of this value from all subsets.
        try:
            val_l = [x[value_list_idx] for x in value_list]
        except Exception as e:
            logger.error("%d # %s", value_list_idx, value_list)
            raise e
    else:
        # If value_list is not a list but a simple value (e.g.: int),
        # take value_list_idx as the numer of subsets and multiply them.
        # --> Same value for all subsets.
        val_l = [value_list] * value_list_idx
    return val_l


def all_one(x):
    """Set all bits of width x to '1'."""
    return (1 << x) - 1


def b2s(n):
    """Builds a string with characters 0 and 1, representing the bits of an integer n."""
    a = 2 if n // 256 else 1
    m = 1 << 8 * a - 1
    return "".join([('1' if n & (m >> i) else '0') for i in range(0, 8 * a)])


def str2dtg(octets, ed=4):
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


def dtg2str(date_time, ed=4):
    """Convert datetime list to string.

    :param date_time: date/time list (y, m, d, H, M, S)
    :return: a string of octets according:
            BUFR Ed.3: year [yy], month, day, hour, minute
            BUFR Ed.4: year [yyyy], month, day, hour, minute, second
    """
    octets = []
    yy = date_time[0]
    if ed == 3:
        octets.append(chr((yy % 100) & 0xFF))
    elif ed == 4:
        octets.append(chr((yy >> 8) & 0xFF))
        octets.append(chr(yy & 0xFF))
    for i in date_time[1:5]:
        octets.append(chr(i & 0xFF))
    if ed == 4:
        octets.append(chr(date_time[5] & 0xFF))
    return "".join(octets)


def descr_is_nil(desc):
    """True if descriptor is null."""
    return desc == 0


def descr_is_data(desc):
    """True if descriptor is Tab-B bin_data descriptor."""
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
    """List all expanded descriptors.

    :param tables: Table-set.
    :param desc3: list of descriptors to expand.
    :return: desc_list, has_backref
    """
    desc_list = []
    stack = [(desc3, 0)]
    try:
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
    except KeyError as e:
        raise BufrTableError("Unknown descriptor: {}".format(e))
    has_backref = any(True
                      for d in desc_list
                      if 222000 <= d < 240000)
    return desc_list, has_backref
