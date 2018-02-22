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
trollbufr.bufr.Bufr
===================
*The* class holding, decoding, and reading a BUFR.

After decoding the meta-information use the iterator over the subsets.

Each subset is held in an instance of class :class:`~trollbufr.read.Subset`, 
which has the iterator function `next_data()` to iterate over all data elements
in this subset.
"""
import tab.load_tables
import read.bufr_sect as sect
from read.subset import Subset
from read.functions import (descr_is_data, descr_is_loop, descr_is_oper,
                            descr_is_seq, descr_is_nil, get_descr_list)
from read.errors import BufrDecodeError, BufrDecodeWarning
from tab.errors import BufrTableError
import logging

logger = logging.getLogger("trollbufr")

# List of supported BUFR editions
SUPPORTED_BUFR_EDITION = (3, 4)


class Bufr(object):
    """Holds and decodes a BUFR"""
    # Holds byte array with bufr
    _blob = None
    # Meta data
    _meta = {}
    # Edition
    _edition = 4
    # Number of subsets
    _subsets = -1
    # Compressed data
    _compressed = False
    # Initial list of descr (from Sect3)
    _desc = []
    # Start of data
    _data_s = -1
    # End of data
    _data_e = -1
    # Path to tables
    _tab_p = None
    # Format of tables
    _tab_f = None
    # Holds table object
    _tables = None

    def __init__(self, tab_fmt, tab_path, data=None):
        self._tab_p = tab_path
        self._tab_f = tab_fmt
        if data is not None:
            self._blob = data
            self._meta = self.decode(data)

    def get_tables(self):
        return self._tables

    def get_meta(self):
        return self._meta

    def get_meta_str(self):
        """All meta-information from section 1+3 as multi-line string"""
        s = []
        t = "%-32s: %s"
        s.append(t % ("Edition",
                      self._meta.get("edition", "---")))
        s.append(t % ("Master-table",
                      self._meta.get("master", "---")))
        cc = self._meta.get("center",
                            "---")
        cs = self._meta.get("subcenter",
                            "---")
        if self._tables is not None:
            cc = self._tables.lookup_codeflag(1033, cc)
            cs = self._tables.lookup_codeflag(1034, cs)
        s.append(t % ("Centre",
                      cc))
        s.append(t % ("Sub-Centre",
                      cs))
        s.append(t % ("Update sequence number",
                      self._meta.get("update", "---")))
        s.append(t % ("Type of data",
                      ("observed" if self._meta.get("obs", 0) else "other")))
        dc = self._meta.get("cat",
                            "---")
        if self._tables is not None:
            dc = self._tables.lookup_common(dc)
        s.append(t % ("Data category",
                      dc))
        s.append(t % ("International data sub-category",
                      self._meta.get("cat_int", "---")))
        s.append(t % ("Local data sub-category",
                      self._meta.get("cat_loc", "---")))
        s.append(t % ("Version number of master table",
                      self._meta.get("mver", "---")))
        s.append(t % ("Version number of local table",
                      self._meta.get("lver", "---")))
        s.append(t % ("Most typical time",
                      self._meta.get("datetime", "---")))
        s.append(t % ("Optional section present",
                      ("yes" if self._meta.get("sect2", False) else "no")))
        s.append(t % ("Compression",
                      ("yes" if self._meta.get("comp", False) else "no")))
        s.append(t % ("Number of data subsets",
                      self._meta.get("subsets", "---")))
        return "\n".join(s)

    def load_tables(self):
        """Load all tables referenced by the BUFR"""
        if not len(self._meta):
            raise BufrTableError("No table loaded!")
        self._tables = tab.load_tables.load_differ(self._tables,
                                                   self._meta['master'],
                                                   self._meta['center'],
                                                   self._meta['subcenter'],
                                                   self._meta['mver'],
                                                   self._meta['lver'],
                                                   self._tab_p,
                                                   self._tab_f
                                                   )
        if self._tables is None:
            raise BufrTableError("No table loaded!")
        return self._tables

    def get_descr_full(self):
        """List descriptors, with unit and name/description"""
        desc_text = []
        dl = get_descr_list(self._tables, self._desc)
        di = 0
        while di < len(dl):
            if descr_is_nil(dl[di]):
                pass
            elif descr_is_data(dl[di]):
                desc_text.append(str(self._tables.tab_b[dl[di]]))
            elif descr_is_loop(dl[di]):
                lm = dl[di] // 1000 - 100
                ln = dl[di] % 1000
                desc_text.append("%06d : LOOP, %d desc., %d times"
                                 % (dl[di], lm, ln))
            elif descr_is_oper(dl[di]):
                if dl[di] in self._tables.tab_c:
                    en = self._tables.tab_c.get(dl[di])
                else:
                    en = self._tables.tab_c.get(dl[di] // 1000)
                am = dl[di] // 1000 - 200
                an = dl[di] % 1000
                if en is None:
                    en = (str(am), "")
                if dl[di] < 222000:
                    desc_text.append("%06d : OPERATOR, %s: %d" % (dl[di], en[0], an))
                else:
                    desc_text.append("%06d : OPERATOR, %s" % (dl[di], en[0]))
            elif descr_is_seq(dl[di]):
                desc_text.append("%06d : SEQUENCE, %d desc." % (dl[di], len(self._tables.tab_d.get(dl[di]))))
            di += 1
        return desc_text

    def get_descr_short(self):
        """List descriptors, unexpanded, no unit nor name/description"""
        desc_text = []
        dl = self._desc
        di = 0
        while di < len(dl):
            if descr_is_nil(dl[di]):
                pass
            elif descr_is_data(dl[di]):
                desc_text.append("%06d" % dl[di])
            elif descr_is_loop(dl[di]):
                desc_text.append("%06d LOOP" % dl[di])
            elif descr_is_oper(dl[di]):
                desc_text.append("%06d OPER" % dl[di])
            elif descr_is_seq(dl[di]):
                desc_text.append("%06d SEQ" % dl[di])
            di += 1
        return desc_text

    def next_subset(self):
        """
        Iterator for subsets in Sect. 4

        .. IMPORTANT::
           allways consume all values from next_data() before retrieving the next report!

        :return: first/next subset object
        :rtype: read.Subset
        :raise BufrDecodeWarning: recoverable error.
        :raise BufrDecodeError: error that stops decoding.
        """
        i = 0
        subset = None
        self._blob.reset(self._data_s)
        # Determine if descriptors need recording for back-reference operator
        self._desc_exp = get_descr_list(self._tables, self._desc)
        self._has_backref_oper = any(True
                                     for d in self._desc_exp
                                     if 222000 <= d < 240000)
        logger.info("BUFR START")
        while i < self._subsets:
            logger.info("SUBSET #%d", i)
            if subset is not None and subset.inprogress:
                raise BufrDecodeWarning("Subset decoding still in progress!")
            # Only if no subset is read currently
            if self._compressed:
                self._blob.reset(self._data_s)
            if self._blob.p >= self._data_e:
                raise BufrDecodeError("Unexpected end of data section!")
            # Create new Subset object
            subset = Subset(self._tables,
                            self._blob,
                            self._desc,
                            self._compressed,
                            self._has_backref_oper,
                            (i, self._subsets),
                            self._data_e)
            yield subset
            i += 1
            # Padding bits (and to next even byte) for data pointer if necessary
            if self._edition < 4:
                data_p = self._blob.p + (self._blob.bc and 1)
                data_p += data_p & 1
                logger.debug("Padding  p:%d  bc:%d  -->  p:%d",
                             self._blob.p, self._blob.bc, data_p)
                self._blob.reset(data_p)
        # Padding bits after last subset
        data_p = self._blob.p + (self._blob.bc and 1)
        self._blob.reset(data_p)
        # Check if sect.5 is reached
        if data_p != self._data_e or self._blob[data_p, data_p + 4] != "7777":
            logger.warning("Data section did not end properly, %d -> '%s'",
                           data_p, self._blob[data_p, data_p + 4])
        logger.info("BUFR END")
        raise StopIteration

    def decode(self, data, tables=True):
        """
        Decodes all meta-data of the BUFR.

        This function prepares the iterators for reading data.

        :param string data: data object with complete BUFR
        :param bool tables: automatically load tables
        :raise BufrDecodeWarning: recoverable error.
        :raise BufrDecodeError: error that stops decoding.
        """
        if data is None or not len(data):
            raise BufrDecodeWarning("Data buffer is empty!")
        self._blob = data
        self._meta = {}
        logger.info("SECT 0..5 DECODE")

        o, l, r = sect.decode_sect0(self._blob, 0)
        self._meta.update(r)
        self._edition = r['edition']
        logger.debug("SECT_0\t offs:%d len:%d = %s", o, l, r)
        if self._edition not in SUPPORTED_BUFR_EDITION:
            raise BufrDecodeError("BUFR edition %d not supported" % self._edition)

        o, l, r = sect.decode_sect1(self._blob, o, edition=self._edition)
        self._meta.update(r)
        logger.debug("SECT_1\t offs:%d len:%d = %s", o, l, r)

        tables_fail = None
        if tables:
            try:
                self._tables = self.load_tables()
            except StandardError or Warning as exc:
                tables_fail = exc

        if r['sect2']:
            o, l, r = sect.decode_sect2(self._blob, o)
            self._meta.update(r)
            logger.debug("SECT_2\t offs:%d len:%d = %s", o, l, r)

        o, l, r = sect.decode_sect3(self._blob, o)
        self._meta.update(r)
        self._subsets = r['subsets']
        self._compressed = r['comp']
        self._desc = r['descr']
        logger.debug("SECT_3\t offs:%d len:%d = %s", o, l, r)

        o, l, r = sect.decode_sect4(self._blob, o)
        self._meta.update(r)
        logger.debug("SECT_4\t offs:%d len:%d = %s", o, l, r)
        self._data_s = r['data_start']
        self._data_e = r['data_end']

        o, l, r = sect.decode_sect5(self._blob, o)
        self._meta.update(r)
        logger.debug("SECT_5\t offs:%d len:%d = %s", o, l, r)

        if o == -1:
            logger.error("End '7777' not found")
            raise BufrDecodeError("End '7777' not found")

        if self._meta['size'] != o:
            logger.error("size/offset error: size %d <> offset %d", self._meta['size'], o)
            raise BufrDecodeError("Size/offset error")

        if tables_fail is not None:
            raise tables_fail

        return self._meta
