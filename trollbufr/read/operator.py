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

    :return: di, (desc,mark,(value,qual))|None
    """
    # Dictionary referencing operator functions from descriptors xx part.
    res = {
        1: fun01,  # Change data width
        2: fun02,  # Change scale
        3: fun03,  # Set of new reference values
        4: fun04,  # Add associated field, shall be followed by 031021
        5: fun05,  # Signify with characters, plain language text as returned value
        6: fun06,  # Length of local descriptor
        7: fun07,  # Change scale, reference, width
        8: fun08,  # Change data width for characters
        9: fun09,  # IEEE floating point representation
        21: fun21,  # Data not present
        22: fun22,  # Quality Assessment Information
        23: funX,  # Substituted values /
        24: fun24,  # First-order statistical values /
        25: funX,  # Difference statistical values /
        32: funX,  # Replaced/retained vaules /
        35: fun35,  # Cancel backward data reference /
        36: fun36,  # Define data present bit-map /
        37: fun37,  # Use data present bit-map / Cancel data present bit-map
        41: funX,  # Define event / Cancel event
        42: funX,  # Define conditioning event / Cancel conditioning event
        43: funX,  # Categorial forecast values follow / Cancel categorial forecast
    }
    # Delegating to operator function from dict.
    logger.debug("OP %d", dl[di])
    am = dl[di] // 1000 - 200
    if am not in res:
        raise BufrDecodeError("Operator %06d not implemented." % dl[di])
    l_di, l_rval = res[am](subset, dl, di, de)
    return l_di, l_rval


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


def fun01(subset, dl, di, _):
    """Change data width"""
    an = dl[di] % 1000
    subset._alter['wnum'] = an - 128 if an else 0
    return di, None


def fun02(subset, dl, di, _):
    """Change scale"""
    an = dl[di] % 1000
    subset._alter['scale'] = an - 128 if an else 0
    return di, None


def fun03(subset, dl, di, de):
    """Set of new reference values"""
    an = dl[di] % 1000
    if an == 0:
        subset._alter['refval'] = {}
    else:
        l_di = subset._read_refval(dl, di, de)
        logger.debug("OP refval -> %s" % subset._alter['refval'])
    return l_di, None


def fun04(subset, dl, di, _):
    """Add associated field, shall be followed by 031021"""
    an = dl[di] % 1000
    # Manages stack for associated field, the value added last shall be used.
    if an == 0:
        subset._alter['assoc'].pop()
        if not len(subset._alter['assoc']):
            subset._alter['assoc'] = [0]
    else:
        subset._alter['assoc'].append(subset._alter['assoc'][-1] + an)
    return di, None


def fun05(subset, dl, di, _):
    """Signify with characters, plain language text as returned value"""
    an = dl[di] % 1000
    foo = fun.get_rval(subset._blob, subset.is_compressed, subset.subs_num, fix_width=an * 8)
    v = fun.rval2str(foo)
    logger.debug("OP text -> '%s'", v)
    # Special rval for plain character
    l_rval = fun.DescrDataEntry(dl[di], None, v, None)
    return di, l_rval


def fun06(subset, dl, di, _):
    """Length of local descriptor"""
    an = dl[di] % 1000
    fun.get_rval(subset._blob, subset.is_compressed, subset.subs_num, fix_width=an)
    l_di = di + 1
    return l_di, None


def fun07(subset, dl, di, _):
    """Change scale, reference, width"""
    an = dl[di] % 1000
    if an == 0:
        subset._alter['scale'] = 0
        subset._alter['refmul'] = 1
        subset._alter['wnum'] = 0
    else:
        subset._alter['scale'] = an
        subset._alter['refmul'] = 10 ^ an
        subset._alter['wnum'] = ((10 * an) + 2) / 3
    return di, None


def fun08(subset, dl, di, _):
    """Change data width for characters"""
    an = dl[di] % 1000
    subset._alter['wchr'] = an * 8 if an else 0
    return di, None


def fun09(subset, dl, di, _):
    """IEEE floating point representation"""
    an = dl[di] % 1000
    subset._alter['ieee'] = an
    return di, None


def fun21(subset, dl, di, _):
    """Data not present"""
    an = dl[di] % 1000
    subset._skip_data = an
    return di, None


def fun22(subset, dl, di, _):
    """Quality Assessment Information"""
    logger.debug("OP %d", dl[di])
    en = subset._tables.tab_c.get(dl[di], ("Operator",))
    # An additional rval for operators where no further action is required
    l_rval = fun.DescrDataEntry(dl[di], None, en[0], None)
    return di, l_rval


def fun24(subset, dl, di, _):
    """First-order statistical values follow."""
    logger.debug("OP %d", dl[di])
    if dl[di] == 224000:
        en = subset._tables.tab_c.get(dl[di], ("Operator",))
        # An additional rval for operators where no further action is required
        l_rval = fun.DescrDataEntry(dl[di], None, en[0], None)

        subset._backref_stack = [subset._backref_record[i]
                                 for i in range(len(subset._bitmap) - 1, 0, -1)
                                 if subset._bitmap[i] == 0]
    elif dl[di] == 224255:
        bar = subset._backref_stack.pop()
        foo = fun.get_rval(subset._blob, subset.is_compressed, subset.subs_num, tab_b_elem=bar[0], alter=bar[1])
        v = fun.rval2num(bar[0], bar[1], foo)
        l_rval = fun.DescrDataEntry(dl[di], None, v, bar[0])
    else:
        raise BufrDecodeError("Unknown operator '%d'!", dl[di])
    return di, l_rval


def fun35(subset, dl, di, _):
    """Cancel backward data reference."""
    if dl[di] == 235000:
        subset._backref_record = []
        subset._do_backref_record = True
    return di, None


def fun36(subset, dl, di, _):
    """Define data present bit-map."""
    # Evaluate following replication descr.
    di += 1
    am = dl[di] // 1000 - 100
    an = dl[di] % 1000
    # Move to data present indicating descr.
    di += 1
    if am != 1 or dl[di] != 31031:
        raise BufrDecodeError("Fault in replication defining bitmap!")
    subset._bitmap = [fun.get_rval(subset._blob, subset.is_compressed, subset.subs_num, fix_width=1) for _ in range(an)]
    subset._do_backref_record = False
    l_rval = fun.DescrDataEntry(dl[di], "BMP", subset._bitmap, None)
    return di, l_rval


def fun37(subset, dl, di, _):
    """Use (237000) or cancel use (237255) defined data present bit-map."""
    if dl[di] == 237000:
        l_rval = fun.DescrDataEntry(dl[di], "BMP", subset._bitmap, None)
    elif dl[di] == 237255:
        subset._bitmap = []
    return di, l_rval


def funX(subset, dl, di, de):
    """Not implemented.

    This is a dummy function for operators who are to expect (as from BUFR
    standard) but are yet not implemented.
    """
    raise NotImplementedError("Operator %06d not implemented." % dl[di])
