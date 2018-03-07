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
import logging

logger = logging.getLogger("trollbufr")


def eval_oper(subset, dl, di, de):
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
        35: fun_35_r,  # Cancel backward data reference
        36: fun_36_r,  # Define data present bit-map
        37: fun_37_r,  # Use data present bit-map / Cancel use data present bit-map
        41: fun_fail,  # Define event / Cancel event
        42: fun_fail,  # Define conditioning event / Cancel conditioning event
        43: fun_fail,  # Categorial forecast values follow / Cancel categorial forecast
    }
    # Delegating to operator function from dict.
    logger.debug("OP %d", dl[di])
    am = dl[di] // 1000 - 200
    if am not in res:
        raise BufrDecodeError("Operator %06d not implemented." % dl[di])
    l_r = res[am](subset, dl, di, de)
    return l_r[0], l_r[1]


def prep_oper(subset, dl, di, de, vl, vi):
    """Evaluate operator, write octets to data section if necessary.

    :return: di, None|DescrDataEntry, vi
    """
    # Dictionary referencing operator functions from descriptors xx part.
    res = {
        1: fun_01,  # Change data width
        2: fun_02,  # Change scale
        3: fun_fail,  # Set of new reference values
        4: fun_04,  # Add associated field, shall be followed by 031021
        5: fun_fail,  # Signify with characters, plain language text as returned value
        6: fun_fail,  # Length of local descriptor
        7: fun_07,  # Change scale, reference, width
        8: fun_08,  # Change data width for characters
        9: fun_09,  # IEEE floating point representation
        21: fun_21,  # Data not present
        22: fun_noop,  # Quality Assessment Information
        23: fun_fail,  # Substituted values operator / Substituted values marker
        24: fun_fail,  # First-order statistical values follow / marker operator
        25: fun_fail,  # Difference statistical values follow / marker operator
        32: fun_fail,  # Replaced/retained vaules follow / marker operator
        35: fun_fail,  # Cancel backward data reference
        36: fun_noop,  # Define data present bit-map
        37: fun_37_w,  # Use data present bit-map / Cancel use data present bit-map
        41: fun_fail,  # Define event / Cancel event
        42: fun_fail,  # Define conditioning event / Cancel conditioning event
        43: fun_fail,  # Categorial forecast values follow / Cancel categorial forecast
    }
    # Delegating to operator function from dict.
    logger.debug("OP %d", dl[di])
    am = dl[di] // 1000 - 200
    if am not in res:
        raise BufrDecodeError("Operator %06d not implemented." % dl[di])
    l_r = res[am](subset, dl, di, de, vl, vi)
    if len(l_r) == 2:
        return l_r[0], l_r[1], vi
    else:
        return l_r


'''
Template for future operator functions.
The subset object is passed to them because they might need access to the
subset's private attributes and methods.

def funXY(subset, dl, di, de):
    """"""
    an = dl[di] % 1000
    if an==0:
        """Define/use/follows"""
        pass
    elif an==255:
        """Cancel"""
        pass
    return di,None
'''


def fun_01(subset, dl, di, _):
    """Change data width"""
    an = dl[di] % 1000
    subset._alter.wnum = an - 128 if an else 0
    return di, None


def fun_02(subset, dl, di, _):
    """Change scale"""
    an = dl[di] % 1000
    subset._alter.scale = an - 128 if an else 0
    return di, None


def fun_03_r(subset, dl, di, de):
    """Set of new reference values"""
    an = dl[di] % 1000
    if an == 0:
        subset._alter.refval = {}
    else:
        l_di = subset._read_refval(dl, di, de)
        logger.debug("OP refval -> %s" % subset._alter.refval)
    return l_di, None


def fun_04(subset, dl, di, _):
    """Add associated field, shall be followed by 031021"""
    an = dl[di] % 1000
    # Manages stack for associated field, the value added last shall be used.
    if an == 0:
        subset._alter.assoc.pop()
        if not len(subset._alter.assoc):
            subset._alter.assoc = [0]
    else:
        subset._alter.assoc.append(subset._alter.assoc[-1] + an)
    return di, None


def fun_05_r(subset, dl, di, _):
    """Signify with characters, plain language text as returned value"""
    an = dl[di] % 1000
    foo = fun.get_rval(subset._blob,
                       subset.is_compressed,
                       subset.subs_num,
                       fix_width=an * 8)
    v = fun.rval2str(foo)
    logger.debug("OP text -> '%s'", v)
    # Special rval for plain character
    l_rval = fun.DescrDataEntry(dl[di], None, v, None)
    return di, l_rval


def fun_06_r(subset, dl, di, _):
    """Length of local descriptor"""
    an = dl[di] % 1000
    fun.get_rval(subset._blob,
                 subset.is_compressed,
                 subset.subs_num,
                 fix_width=an)
    l_di = di + 1
    return l_di, None


def fun_07(subset, dl, di, _):
    """Change scale, reference, width"""
    an = dl[di] % 1000
    if an == 0:
        subset._alter.scale = 0
        subset._alter.refmul = 1
        subset._alter.wnum = 0
    else:
        subset._alter.scale = an
        subset._alter.refmul = 10 ^ an
        subset._alter.wnum = ((10 * an) + 2) / 3
    return di, None


def fun_08(subset, dl, di, _):
    """Change data width for characters"""
    an = dl[di] % 1000
    subset._alter.wchr = an * 8 if an else 0
    return di, None


def fun_09(subset, dl, di, _):
    """IEEE floating point representation"""
    an = dl[di] % 1000
    subset._alter.ieee = an
    return di, None


def fun_21(subset, dl, di, _):
    """Data not present"""
    an = dl[di] % 1000
    subset._skip_data = an
    return di, None


def fun_22_r(subset, dl, di, _):
    """Quality Assessment Information"""
    logger.debug("OP %d", dl[di])
    en = subset._tables.tab_c.get(dl[di], ("Operator",))
    # An additional rval for operators where no further action is required
    l_rval = fun.DescrDataEntry(dl[di], "OPR", en[0], None)
    return di, l_rval


def fun_24_r(subset, dl, di, _):
    """First-order statistical values."""
    an = dl[di] % 1000
    return fun_statistic_read(subset, dl, di, an)


def fun_25_r(subset, dl, di, _):
    """Difference statistical values."""
    an = dl[di] % 1000
    return fun_statistic_read(subset, dl, di, an)


def fun_statistic_read(subset, dl, di, an):
    """Various operators for statistical values."""
    logger.debug("OP %d", dl[di])
    if an == 0:
        """Statistical values follow."""
        en = subset._tables.tab_c.get(dl[di], ("Operator",))
        # Local return value: long name of this operator.
        l_rval = fun.DescrDataEntry(dl[di], "OPR", en[0], None)

        subset._backref_stack = [subset._backref_record[i]
                                 for i in range(len(subset._bitmap) - 1, 0, -1)
                                 if subset._bitmap[i] == 0]
    elif an == 255:
        """Statistical values marker operator."""
        bar = subset._backref_stack.pop()
        foo = fun.get_rval(subset._blob,
                           subset.is_compressed,
                           subset.subs_num,
                           tab_b_elem=bar[0],
                           alter=bar[1])
        v = fun.rval2num(bar[0], bar[1], foo)
        l_rval = fun.DescrDataEntry(dl[di], None, v, bar[0])
    else:
        raise BufrDecodeError("Unknown operator '%d'!", dl[di])
    return di, l_rval


def fun_35_r(subset, dl, di, _):
    """Cancel backward data reference."""
    if dl[di] == 235000:
        subset._backref_record = []
        subset._do_backref_record = True
    return di, None


def fun_36_r(subset, dl, di, _):
    """Define data present bit-map."""
    # Evaluate following replication descr.
    di += 1
    am = dl[di] // 1000 - 100
    an = dl[di] % 1000
    # Move to data present indicating descr.
    di += 1
    if am != 1 or dl[di] != 31031:
        raise BufrDecodeError("Fault in replication defining bitmap!")
    subset._bitmap = [fun.get_rval(subset._blob,
                                   subset.is_compressed,
                                   subset.subs_num,
                                   fix_width=1)
                      for _ in range(an)]
    subset._do_backref_record = False
    l_rval = fun.DescrDataEntry(dl[di], "BMP", subset._bitmap, None)
    return di, l_rval


def fun_37_r(subset, dl, di, _):
    """Use (237000) or cancel use (237255) defined data present bit-map."""
    if dl[di] == 237000:
        l_rval = fun.DescrDataEntry(dl[di], "BMP", subset._bitmap, None)
    elif dl[di] == 237255:
        subset._bitmap = []
    return di, l_rval


def fun_37_w(*args):
    """Skip a bitmap list if one is present in the json data set."""
    if isinstance(args[-2], (list, tuple)):
        return args[2], None, args[-1] + 1
    else:
        return args[2], None


def fun_noop(*args):
    """No further acton required.

    :param args: list, at least [subset, dl, di, de]:
    """
    return args[2], None


def fun_fail(*args):
    """Not implemented.

    This is a dummy function for operators who are to expect (as from BUFR
    standard) but are yet not implemented.

    :param args: list, at least [subset, dl, di, de]:
    """
    raise NotImplementedError("Operator %06d not implemented." % args[1][args[2]])
