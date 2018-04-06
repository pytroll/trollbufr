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
"""
Functions implementing the set of operator descriptors.

Created on Mar 31, 2017

@author: amaul
"""
import functions as fun
from errors import BufrDecodeError
from bufr_types import DescrDataEntry, TabBType
import logging

logger = logging.getLogger("trollbufr")


def eval_oper(subset, descr):
    """Evaluate operator, read octets from data section if necessary.

    :return: di, None|DescrDataEntry(desc,mark,value,qual)
    """
    # Dictionary referencing operator functions from descriptors xx part.
    res = {
        1: fun_01,  # Change data width
        2: fun_02,  # Change scale
        3: fun_03_r,  # Set of new reference values
        4: fun_04,  # Add associated field, shall be followed by 031021
        5: fun_05_r,  # Signify with characters, plain language text as returned value
        6: fun_06_r,  # Length of local descriptor
        7: fun_07,  # Change scale, reference, width
        8: fun_08,  # Change data width for characters
        9: fun_09,  # IEEE floating point representation
        21: fun_21,  # Data not present
        22: fun_22_r,  # Quality Assessment Information
        23: fun_fail,  # Substituted values operator / Substituted values marker
        24: fun_24_r,  # First-order statistical values follow / marker operator
        25: fun_25_r,  # Difference statistical values follow / marker operator
        32: fun_fail,  # Replaced/retained vaules follow / marker operator
        35: fun_35,  # Cancel backward data reference
        36: fun_36_r,  # Define data present bit-map
        37: fun_37_r,  # Use data present bit-map / Cancel use data present bit-map
        41: fun_fail,  # Define event / Cancel event
        42: fun_fail,  # Define conditioning event / Cancel conditioning event
        43: fun_fail,  # Categorial forecast values follow / Cancel categorial forecast
    }
    # Delegating to operator function from dict.
    logger.debug("OP %d", descr)
    am = descr // 1000 - 200
    if am not in res:
        raise BufrDecodeError("Operator %06d not implemented." % descr)
    return res[am](subset, descr)


def prep_oper(subset, descr):
    """Evaluate operator, write octets to data section if necessary.

    :return: di, None|DescrDataEntry, vi
    """
    # Dictionary referencing operator functions from descriptors xx part.
    res = {
        1: fun_01,  # Change data width
        2: fun_02,  # Change scale
        3: fun_03_w,  # Set of new reference values
        4: fun_04,  # Add associated field, shall be followed by 031021
        5: fun_05_w,  # Signify with characters, plain language text as returned value
        6: fun_noop,  # Length of local descriptor
        7: fun_07,  # Change scale, reference, width
        8: fun_08,  # Change data width for characters
        9: fun_09,  # IEEE floating point representation
        21: fun_21,  # Data not present
        22: fun_noop,  # Quality Assessment Information
        23: fun_fail,  # Substituted values operator / Substituted values marker
        24: fun_24_w,  # First-order statistical values follow / marker operator
        25: fun_25_w,  # Difference statistical values follow / marker operator
        32: fun_fail,  # Replaced/retained vaules follow / marker operator
        35: fun_35,  # Cancel backward data reference
        36: fun_36_w,  # Define data present bit-map
        37: fun_37_w,  # Use data present bit-map / Cancel use data present bit-map
        41: fun_fail,  # Define event / Cancel event
        42: fun_fail,  # Define conditioning event / Cancel conditioning event
        43: fun_fail,  # Categorial forecast values follow / Cancel categorial forecast
    }
    # Delegating to operator function from dict.
    logger.debug("OP %d", descr)
    am = descr // 1000 - 200
    if am not in res:
        raise BufrDecodeError("Operator %06d not implemented." % descr)
    return res[am](subset, descr)


'''
Template for future operator functions.
The subset object is passed to them because they might need access to the
subset's private attributes and methods.

def funXY(subset, dl, di, de):
    """"""
    an = descr % 1000
    if an==0:
        """Define/use/follows"""
        pass
    elif an==255:
        """Cancel"""
        pass
    return di,None
'''


def fun_01(subset, descr):
    """Change data width"""
    an = descr % 1000
    subset._alter.wnum = an - 128 if an else 0
    return None


def fun_02(subset, descr):
    """Change scale"""
    an = descr % 1000
    subset._alter.scale = an - 128 if an else 0
    return None


def fun_03_r(subset, descr):
    """Set of new reference values"""
    an = descr % 1000
    if an == 0:
        subset._alter.refval = {}
    else:
        subset._read_refval(subset)
        logger.debug("OP refval -> %s" % subset._alter.refval)
    return None


def fun_03_w(subset, descr):
    """Write and set of new reference values"""
    an = descr % 1000
    if an == 0:
        subset._alter.refval = {}
    else:
        subset._write_refval(subset)
        logger.debug("OP refval -> %s" % subset._alter.refval)
    return None


def fun_04(subset, descr):
    """Add associated field, shall be followed by 031021"""
    an = descr % 1000
    # Manages stack for associated field, the value added last shall be used.
    if an == 0:
        subset._alter.assoc.pop()
        if not len(subset._alter.assoc):
            subset._alter.assoc = [0]
    else:
        subset._alter.assoc.append(subset._alter.assoc[-1] + an)
    return None


def fun_05_r(subset, descr):
    """Signify with characters, plain language text as returned value"""
    an = descr % 1000
    foo = fun.get_rval(subset._blob,
                       subset.is_compressed,
                       subset.subs_num,
                       fix_width=an * 8)
    v = fun.rval2str(foo)
    logger.debug("OP text -> '%s'", v)
    # Special rval for plain character
    l_rval = DescrDataEntry(descr, None, v, None)
    return l_rval


def fun_05_w(subset, descr):
    """Signify with characters, plain language text."""
    an = descr % 1000
    logger.debug("OP text %d B -> '%s'", an, subset._vl[subset._vi])
    subset.add_val(subset._blob,
                   subset._vl,
                   subset._vi,
                   fix_width=an * 8,
                   fix_typ=TabBType.STRING)
    return None


def fun_06_r(subset, descr):
    """Length of local descriptor"""
    an = descr % 1000
    fun.get_rval(subset._blob,
                 subset.is_compressed,
                 subset.subs_num,
                 fix_width=an)
    subset._di += 1
    return None


def fun_07(subset, descr):
    """Change scale, reference, width"""
    an = descr % 1000
    if an == 0:
        subset._alter.scale = 0
        subset._alter.refmul = 1
        subset._alter.wnum = 0
    else:
        subset._alter.scale = an
        subset._alter.refmul = 10 ^ an
        subset._alter.wnum = ((10 * an) + 2) / 3
    return None


def fun_08(subset, descr):
    """Change data width for characters"""
    an = descr % 1000
    subset._alter.wchr = an * 8 if an else 0
    return None


def fun_09(subset, descr):
    """IEEE floating point representation"""
    an = descr % 1000
    subset._alter.ieee = an
    return None


def fun_21(subset, descr):
    """Data not present"""
    an = descr % 1000
    subset._skip_data = an
    return None


def fun_22_r(subset, descr):
    """Quality Assessment Information"""
    logger.debug("OP %d", descr)
    en = subset._tables.tab_c.get(descr, ("Operator",))
    # An additional rval for operators where no further action is required
    l_rval = DescrDataEntry(descr, "OPR", en[0], None)
    return l_rval


def fun_24_r(subset, descr):
    """First-order statistical values."""
    an = descr % 1000
    return fun_statistic_read(subset, descr, an)


def fun_24_w(subset, descr):
    """First-order statistical values."""
    an = descr % 1000
    return fun_statistic_write(subset, descr, an)


def fun_25_r(subset, descr):
    """Difference statistical values."""
    an = descr % 1000
    return fun_statistic_read(subset, descr, an)


def fun_25_w(subset, descr):
    """Difference statistical values."""
    an = descr % 1000
    return fun_statistic_write(subset, descr, an)


def fun_statistic_read(subset, descr, an):
    """Various operators for statistical values."""
    logger.debug("OP %d", descr)
    if an == 0:
        """Statistical values follow."""
        en = subset._tables.tab_c.get(descr, ("Operator",))
        # Local return value: long name of this operator.
        l_rval = DescrDataEntry(descr, "OPR", en[0], None)
    elif an == 255:
        """Statistical values marker operator."""
        bar = subset._backref_record.next()
        foo = fun.get_rval(subset._blob,
                           subset.is_compressed,
                           subset.subs_num,
                           tab_b_elem=bar[0],
                           alter=bar[1])
        v = fun.rval2num(bar[0], bar[1], foo)
        l_rval = DescrDataEntry(descr, None, v, bar[0])
    else:
        raise BufrDecodeError("Unknown operator '%d'!", descr)
    return l_rval


def fun_statistic_write(subset, descr, an):
    """Various operators for statistical values."""
    logger.debug("OP %d", descr)
    if an == 0:
        """Statistical values follow."""
        # Filter back-references by bitmap
    elif an == 255:
        """Statistical values marker operator."""
        bar = subset._backref_record.next()
        subset.add_val(subset._blob, subset._vl, subset._vi, tab_b_elem=bar[0], alter=bar[1])
        subset._vi += 1
    else:
        raise BufrDecodeError("Unknown operator '%d'!", descr)
    return None


def fun_35(subset, descr):
    """Cancel backward data reference."""
    if descr == 235000:
        subset._backref_record.restart()
    return None


def fun_36_r(subset, descr):
    """Define data present bit-map."""
    # Evaluate following replication descr.
    subset._di += 1
    am = subset._dl[subset._di] // 1000 - 100
    an = subset._dl[subset._di] % 1000
    # Move to data present indicating descr.
    subset._di += 1
    if am != 1 or subset._dl[subset._di] != 31031:
        raise BufrDecodeError("Fault in replication defining bitmap!")
    subset._bitmap = [fun.get_rval(subset._blob,
                                   subset.is_compressed,
                                   subset.subs_num,
                                   fix_width=1)
                      for _ in range(an)]
    subset._backref_record.apply(subset._bitmap)
    l_rval = DescrDataEntry(descr, "BMP DEF", subset._bitmap, None)
    return l_rval


def fun_36_w(subset, _):
    """Define data present bit-map."""
    # The current index _vi shall point to a "bitmap" list, which shall be a
    # list of single-item lists, i.e. [[1],[1],[0],[1]]
    if subset.is_compressed:
        subset._bitmap = [x[0] for x in fun.mk_value_list(subset._vl, subset._vi)[0]]
    else:
        subset._bitmap = [x[0] for x in subset._vl[subset._vi]]
    subset._backref_record.apply(subset._bitmap)
    return None


def fun_37_r(subset, descr):
    """Use (237000) or cancel use (237255) defined data present bit-map."""
    if descr == 237000:
        l_rval = DescrDataEntry(descr, "BMP USE", subset._bitmap, None)
        subset._backref_record.reset()
    elif descr == 237255:
        subset._bitmap = []
        subset._backref_record.renew()
    return l_rval


def fun_37_w(subset, descr):
    """Use (237000) or cancel use (237255) defined data present bit-map.

    Skip a bitmap list if one is present in the json data set.
    """
    if descr == 237000:
        if ((subset.is_compressed
             and isinstance(subset._vl[0][subset._vi], (list, tuple)))
                or
                (not subset.is_compressed
                 and isinstance(subset._vl[subset._vi], (list, tuple)))
            ):
            subset._vi += 1
        subset._backref_record.reset()
    elif descr == 237255:
        subset._bitmap = []
        subset._backref_record.renew()
    return None


def fun_noop(*_):
    """No further acton required.

    :param args: list, at least [subset, dl, di, de]:
    """
    return None


def fun_fail(_, descr):
    """Not implemented.

    This is a dummy function for operators who are to expect (as from BUFR
    standard) but are yet not implemented.

    :param args: list, at least [subset, dl, di, de]:
    """
    raise NotImplementedError("Operator %06d not implemented." % descr)
