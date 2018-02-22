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
trollbufr-Subset
================
The class doing all decoding, table-loading, etc in the right order.

Created on Oct 28, 2016

@author: amaul
"""
import functions as fun
import operator as op
from copy import deepcopy
from errors import BufrDecodeError
import logging

logger = logging.getLogger("trollbufr")


class Subset(object):
    # Numbering of this subset (this, total)
    subs_num = (-1, -1)
    # Compression
    is_compressed = False
    # Currently decoding a subset
    inprogress = False

    def __init__(self, tables, bufr, descr_list, is_compressed, has_backref, subset_num, data_end):
        self.is_compressed = is_compressed
        self.subs_num = subset_num
        # Holds table object
        self._tables = tables
        # Holds byte array with bufr
        self._blob = bufr
        # Initial descriptor list
        self._desc = descr_list
        # End of data for all subsets
        self._data_e = -1
        # Alterator values
        self._alter = AlterState()
        # Skip N data descriptors
        self._skip_data = 0
        # Recording descriptors for back-referencing
        self._do_backref_record = has_backref
        # Recorder for back-referenced descriptors
        self._backref_record = []
        # Last octet in BUFR
        self._data_e = data_end

    def __str__(self):
        return "Subset #%d/%d, decoding:%s" % (self.subs_num, self.inprogress)

    def next_data(self):
        """Iterator for Sect. 4 data.

        This generator will decode BUFR data.

        For each data element a named tuple is returned. 
        The items are the descriptor, a type marker, a numerical value, and quality information.
        Items unset or unapplicaple are set to None.

        mark consists of three uppercase letters, a space character, and a 
        descriptor or iteration number or "END".
        When a value for mark is returned, the others items are usually None, 
        mark has the meaning:
        - SEQ desc : Following descriptors by expansion of sequence descriptor desc.
        - SEQ END  : End of sequence expansion.
        - RPL #n   : Descriptor replication number #n begins.
        - RPL END  : End of descriptor replication.
        - RPL NIL  : Descriptor replication evaluated to zero replications.
        - REP #n   : Descriptor and data repetition, all descriptor and data between
                     this and REP END are to be repeated #n times.
        - REP END  : End of desriptor and data repetition.
        - BMP      : Use the data present bit-map to refer to the data descriptors 
                     which immediately precede the operator to which it relates.
                     The bitmap is returned in the named tuple item 'value'.

        :yield: collections.namedtuple(desc, mark, value, quality)
        """
        if self._blob.p < 0 or self._data_e < 0 or self._blob.p >= self._data_e:
            raise BufrDecodeError("Data section start/end not initialised!")
        logger.debug("SUBSET START")
        self.inprogress = True
        # Stack for sequence expansion and loops.
        # Items follow: ([desc,], start, end, mark)
        stack = []
        # Alterator values, this resets them at the beginning of the iterator.
        self._alter.reset()
        # For start put list on stack
        logger.debug("PUSH start -> *%d %d..%d", len(self._desc), 0, len(self._desc))
        stack.append((self._desc, 0, len(self._desc), "SUB"))
        while len(stack):
            """Loop while descriptor lists on stack"""
            # dl : current descriptor list
            # di : index for current descriptor list
            # de : stop when reaching this index
            dl, di, de, mark = stack.pop()
            logger.debug("POP *%d %d..%d (%s)", len(dl), di, de, mark)
            yield fun.DescrDataEntry(None, mark, None, None)
            mark = None
            while di < de and self._blob.p < self._data_e:
                """Loop over descriptors in current list"""

                if self._skip_data:
                    """Data not present: data is limited to class 01-09,31"""
                    logger.debug("skip %d", self._skip_data)
                    self._skip_data -= 1
                    if 1000 <= dl[di] < 10000 and dl[di] // 1000 != 31:
                        di += 1
                        continue

                if fun.descr_is_nil(dl[di]):
                    """Null-descriptor to signal end-of-list"""
                    di += 1

                elif fun.descr_is_data(dl[di]):
                    """Element descriptor, decoding bits to value"""
                    # Associated fields (for qualifier) preceede the elements value,
                    # their width is set by an operator descr.
                    # They are handled in compression in same manner as other descr,
                    # with fix width from assoc-field-stack.
                    if self._alter.assoc[-1] and (dl[di] < 31000 or dl[di] > 32000):
                        qual = fun.get_rval(self._blob, self.is_compressed, self.subs_num,
                                            fix_width=self._alter.assoc[-1])
                    else:
                        qual = None
                    elem_b = self._tables.tab_b[dl[di]]
                    di += 1
                    foo = fun.get_rval(self._blob, self.is_compressed, self.subs_num, elem_b, self._alter)
                    v = fun.rval2num(elem_b, self._alter, foo)
                    if self._do_backref_record:
                        self._backref_record.append((elem_b, deepcopy(self._alter)))
                    # This is the main yield
                    yield fun.DescrDataEntry(elem_b.descr, mark, v, qual)

                elif fun.descr_is_loop(dl[di]):
                    """Replication descriptor, loop/iterator, replication or repetition"""
                    # Decode loop-descr:
                    # amount of descr
                    lm = dl[di] // 1000 - 100
                    # number of replication
                    ln = dl[di] % 1000
                    # Repetition?
                    is_repetition = False
                    loop_cause = dl[di]
                    # Increase di to start-of-loop
                    di += 1
                    if ln == 0:
                        # Decode next descr for loop-count
                        if dl[di] < 30000 or dl[di] >= 40000:
                            raise BufrDecodeError("No count for  delayed loop!")
                        elem_b = self._tables.tab_b[dl[di]]
                        di += 1
                        ln = fun.get_rval(self._blob, self.is_compressed, self.subs_num, fix_width=elem_b.width)
                        # Descriptors 31011+31012 mean repetition, not replication
                        is_repetition = 31010 <= elem_b.descr <= 31012
                        logger.debug("%s %d %d -> %d from %06d",
                                     "REPT" if is_repetition else "LOOP", lm, 0, ln, elem_b.descr)
                        if ln == 255:
                            ln = 0
                    else:
                        logger.debug("LOOP %d %d" % (lm, ln))
                    loop_count = ln
                    # Current list on stack (di points after looped descr)
                    logger.debug("PUSH jump -> *%d %d..%d", len(dl), di + lm, de)
                    if is_repetition:
                        if ln:
                            stack.append((dl, di + lm, de, "REP END"))
                            stack.append((dl, di, di + lm, "REP %d" % ln))
                        else:
                            stack.append((dl, di + lm, de, "REP NIL"))
                    else:
                        stack.append((dl, di + lm, de, "RPL %s" % ("END" if ln else "NIL")))
                        while ln:
                            # N*list on stack
                            logger.debug("PUSH loop -> *%d %d..%d", len(dl), di, di + lm)
                            stack.append((dl, di, di + lm, "RPL %d" % ln))
                            ln -= 1
                    yield fun.DescrDataEntry(None,
                                             "%s %06d *%d" % (
                                                 "REP" if is_repetition else "RPL",
                                                 loop_cause,
                                                 loop_count),
                                             None,
                                             None)
                    # Causes inner while to end
                    di = de

                elif fun.descr_is_oper(dl[di]):
                    """Operator descritor, alter/modify properties"""
                    di, v = op.eval_oper(self, dl, di, de)
                    if v is not None:
                        # If the operator returned a value, yield it
                        yield v
                    di += 1

                elif fun.descr_is_seq(dl[di]):
                    """Sequence descriptor, replaces current descriptor with expansion"""
                    logger.debug("SEQ %06d", dl[di])
                    # Current on stack
                    logger.debug("PUSH jump -> *%d %d..%d", len(dl), di + 1, de)
                    stack.append((dl, di + 1, de, "SEQ END"))
                    prevdesc = dl[di]
                    # Sequence from tabD
                    dl = self._tables.tab_d[dl[di]]
                    # Expansion on stack
                    logger.debug("PUSH seq -> *%d %d..%d", len(dl), 0, len(dl))
                    stack.append((dl, 0, len(dl), "SEQ %06d" % prevdesc))
                    # Causes inner while to end
                    di = de

                else:
                    """Invalid descriptor, out of defined range"""
                    raise BufrDecodeError("Descriptor '%06d' invalid!" % dl[di])

        self.inprogress = False
        logger.debug("SUBSET END (%s)" % self._blob)
        raise StopIteration

    def _read_refval(self, dl, di, de):
        """Set new reference values.

        Reads a set of YYY bits, taking them as new reference values for the descriptors of the set.
        YYY is taken from the current descriptor dl[di], reference values are set for
        all subsequent following descriptors until the descriptor signaling the end of operation occurs.

        :return: number of new reference values
        """
        i = di
        rl = {}
        an = dl[i] % 1000
        i += 1
        while i < de:
            rval = fun.get_rval(self._blob, self.is_compressed, self.subs_num, fix_width=an)
            # Sign=high-bit
            sign = -1 if (1 << (an - 1)) & rval else 1
            # Value=val&(FFF>>1)
            val = ((1 << an) - 1) & rval
            rl[dl[i]] = sign * val
            i += 1
            if dl[i] > 200000 and dl[i] % 1000 == 255:
                # YYY==255 is signal-of-end
                break
        self._alter.refval = rl
        return i


class AlterState(object):
    def __init__(self):
        self.reset()

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
