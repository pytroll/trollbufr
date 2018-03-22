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
Collection of classes.

Created on Mar 13, 2018

@author: amaul
"""

from collections import namedtuple
DescrDataEntry = namedtuple("DescrDataEntry", "descr mark value quality")
"""Description of 'mark' for non-data types:
SEQ desc : Following descriptors by expansion of sequence descriptor desc.
SEQ END  : End of sequence expansion.
RPL #n   : Descriptor replication number #n begins.
RPL END  : End of descriptor replication.
RPL NIL  : Descriptor replication evaluated to zero replications.
REP #n   : Descriptor and data repetition, all descriptor and data between
           this and REP END are to be repeated #n times.
REP END  : End of desriptor and data repetition.
OPR desc : Operator, which read and returned data values. 
BMP DEF  : Use the data present bit-map to refer to the data descriptors 
           which immediately precede the operator to which it relates.
           The bitmap is returned in the named tuple item 'value'.
BMP USE  : Re-use the previously defined data present bit-map. Same as "BMP DEF".
"""

BufrMetadataKeys = ("master",  # BUFR master version, WMO=0.
                    "center",  # Originating center.
                    "subcenter",  # Originating sub-center.
                    "update",  # Update number.
                    "sect2",  # Section 2 (local data) present.
                    "cat",  # Data category.
                    "cat_int",  # International data category.
                    "cat_loc",  # Local data category.
                    "mver",  # Master table version.
                    "lver",  # Local table version.
                    "datetime",  # Associated date/time.
                    "obs",  # Observed data.
                    "comp",  # Compression used.
                    )


class TabBType(object):
    """Types of Table-B entries."""
    NUMERIC = 0
    LONG = 1
    DOUBLE = 2
    CODE = 3
    FLAG = 4
    STRING = 5


class AlterState(object):
    """Holding the states for altering descriptors."""

    def __init__(self):
        self.reset()

    def __str__(self):
        return "wnum={} wchr={} refmul={} scale={} assoc={} ieee={} refval={}".format(
            self.wnum, self.wchr, self.refmul, self.scale, self.assoc[-1], self.ieee, self.refval
        )

    def reset(self):
        self.wnum = 0
        """Add to width, for number data fields."""
        self.wchr = 0
        """ Change width for string data fields."""
        self.refval = {}
        """ {desc:ref}, dict with new reference values for descriptors."""
        self.refmul = 1
        """ Multiplier, for all reference values of following descriptors (207yyy)."""
        self.scale = 0
        """ Add to scale, for number data fields."""
        self.assoc = [0]
        """ Add width for associated quality field. A stack, always use last value."""
        self.ieee = 0
        """ 0|32|64 All numerical values encoded as IEEE floating point number."""
