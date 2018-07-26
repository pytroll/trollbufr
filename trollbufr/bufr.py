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
which has the iterator function `next_data()` to iterate over all bin_data elements
in this subset.
"""
from coder.load_tables import TableCache
import coder.bufr_sect as sect
from coder.subset import SubsetReader, SubsetWriter
from coder.bdata import Blob
from coder.tables import TabBElem
from coder.functions import (descr_is_data, descr_is_loop, descr_is_oper,
                             descr_is_seq, descr_is_nil, get_descr_list)
from coder.errors import (SUPPORTED_BUFR_EDITION, BufrDecodeError,
                          BufrDecodeWarning, BufrTableError, BufrEncodeError)
import logging

logger = logging.getLogger("trollbufr")


class Bufr(object):
    """Holds and decodes a BUFR"""
    # Holds byte-array-like object with bufr
    _blob = None
    # Meta bin_data
    _meta = {}
    # Initial list of descr (from Sect3)
    _desc = []
    # Start of bin_data
    _data_s = -1
    # End of bin_data
    _data_e = -1
    # Path to tables
    _tab_p = None
    # Format of tables
    _tab_f = None
    # Holds table object
    _table_cache = None
    _tables = None
    # Edition
    edition = 4
    # Number of subsets
    subsets = -1
    # Compressed bin_data
    is_compressed = False

    def __init__(self, tab_fmt, tab_path, bin_data=None, json_obj=None):
        self._tab_p = tab_path
        self._tab_f = tab_fmt
        self._table_cache = TableCache(tab_path, tab_fmt)
        if bin_data is not None:
            self._blob = bin_data
            self._meta = self.decode(bin_data)
        elif json_obj is not None:
            self._meta = self.encode(json_obj)

    def get_tables(self):
        return self._tables

    def get_meta(self):
        return self._meta

    def get_supported_edition(self):
        return SUPPORTED_BUFR_EDITION

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
        self._tables = self._table_cache.load(self._meta['master'],
                                              self._meta['center'],
                                              self._meta['subcenter'],
                                              self._meta['mver'],
                                              self._meta['lver'],
                                              )
        if self._tables is None:
            raise BufrTableError("No table loaded!")
        return self._tables

    def get_descr_full(self):
        """List descriptors, with unit and name/description"""
        desc_text = []
        dl, _ = get_descr_list(self._tables, self._desc)
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

    def next_subset_array(self):
        logger.info("SUBSETS %d", self.subsets)
        if self._blob.p >= self._data_e:
            raise StopIteration
        # Create new Subset object
        subset = SubsetReader(self._tables,
                              self._blob,
                              self._desc,
                              self.is_compressed,
                              (-1, self.subsets),
                              self._data_e,
                              edition=self.edition,
                              has_backref=self._has_backref_oper,
                              as_array=True)
        yield subset
        # Padding bits (and to next even byte) for bin_data pointer if necessary
        if self.edition < 4:
            p = self._blob.p
            bc = self._blob.bc
            self._blob.read_align(even=True)
            logger.debug("Padding  p:%d  bc:%d  -->  p:%d",
                         p, bc, self._blob.p)
        raise StopIteration

    def next_subset_single(self):
        subset = None
        for i in range(self.subsets):
            logger.info("SUBSET #%d", i)
            if subset is not None and subset.inprogress:
                raise BufrDecodeWarning("Subset decoding still in progress!")
            # Only if no subset is read currently
            if self.is_compressed:
                self._blob.reset(self._data_s)
            if self._blob.p >= self._data_e:
                raise BufrDecodeError("Unexpected end of bin_data section!")
            # Create new Subset object
            subset = SubsetReader(self._tables,
                                  self._blob,
                                  self._desc,
                                  self.is_compressed,
                                  (i, self.subsets),
                                  self._data_e,
                                  has_backref=self._has_backref_oper)
            yield subset
            i += 1
            # Padding bits (and to next even byte) for bin_data pointer if necessary
            if self.edition < 4:
                p = self._blob.p
                bc = self._blob.bc
                self._blob.read_align(even=True)
                logger.debug("Padding  p:%d  bc:%d  -->  p:%d",
                             p, bc, self._blob.p)
        raise StopIteration

    def next_subset(self, as_array=False):
        """Iterator for subsets in Sect. 4

        .. IMPORTANT::
           allways consume all values from next_data() before retrieving the next report!

        :return: first/next subset object
        :rtype: read.Subset
        :raise BufrDecodeWarning: recoverable error.
        :raise BufrDecodeError: error that stops decoding.
        """
        self._blob.reset(self._data_s)
        # Determine if descriptors need recording for back-reference operator
        self._desc_exp, self._has_backref_oper = get_descr_list(self._tables, self._desc)
        logger.info("BUFR START")
        if as_array:
            for subset in self.next_subset_array():
                yield subset
        else:
            for subset in self.next_subset_single():
                yield subset
        # Padding bits after last subset
        self._blob.read_align()
        # Check if sect.5 is reached
        if self._blob.p != self._data_e:
            logger.warning("Data section did not end properly, %d <> %d",
                           self._blob.p, self._data_e)
        logger.info("BUFR END")
        raise StopIteration

    def decode_meta(self, bin_data, load_tables=True):
        """Decodes all meta-data of the BUFR.

        This function prepares the iterators for reading data.

        :param bin_data: Blob: data object with complete BUFR.
        :param load_tables: bool: automatically load load_tables.
        :raise BufrDecodeWarning: recoverable error.
        :raise BufrDecodeError: error that stops decoding.
        """
        if bin_data is None or not len(bin_data):
            raise BufrDecodeWarning("Data buffer is empty!")
        self._blob = bin_data
        self._meta = {}
        logger.info("SECT 0..5 DECODE")
        #
        # Section 0
        #
        o, l, r = sect.decode_sect0(self._blob, 0)
        self._meta.update(r)
        self.edition = r['edition']
        logger.debug("SECT_0\t offs:%d len:%d = %s", o, l, r)
        if self.edition not in SUPPORTED_BUFR_EDITION:
            raise BufrDecodeError("BUFR edition %d not supported" % self.edition)
        #
        # Section 1
        #
        o, l, r = sect.decode_sect1(self._blob, o, edition=self.edition)
        self._meta.update(r)
        logger.debug("SECT_1\t offs:%d len:%d = %s", o, l, r)

        tables_fail = None
        if load_tables:
            try:
                self._tables = self.load_tables()
            except StandardError or Warning as exc:
                tables_fail = exc
        #
        # Section 2
        #
        if r['sect2']:
            o, l, r = sect.decode_sect2(self._blob, o)
            self._meta.update(r)
            logger.debug("SECT_2\t offs:%d len:%d = %s", o, l, r)
        #
        # Section 3
        #
        o, l, r = sect.decode_sect3(self._blob, o)
        self._meta.update(r)
        self.subsets = r['subsets']
        self.is_compressed = r['comp']
        self._desc = r['descr']
        logger.debug("SECT_3\t offs:%d len:%d = %s", o, l, r)
        #
        # Section 4
        #
        o, l, r = sect.decode_sect4(self._blob, o)
        self._meta.update(r)
        logger.debug("SECT_4\t offs:%d len:%d = %s", o, l, r)
        self._data_s = r['data_start']
        self._data_e = r['data_end']
        #
        # Section 5
        #
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

    def decode(self, bin_data, load_tables=True, as_array=False):
        """Decodes the BUFR into a JSON compatible data object.

        The created JSON compatible data object is a list of the BUFR sections,
        where each section itself is a list of the values, in the same order as
        stored in a BUFR.

        :param bin_data: Blob: data object with complete BUFR.
        :param load_tables: bool: automatically load load_tables.
        :return: JSON object
        :raise BufrDecodeWarning: recoverable error.
        :raise BufrDecodeError: error that stops decoding.
        """
        self.decode_meta(bin_data, load_tables)
        json_bufr = []
        #
        # Section 0
        #
        json_bufr.append(["BUFR", self._meta["edition"]])
        #
        # Section 1
        #
        if self._meta["edition"] == 3:
            mkeys = ("master", "subcenter", "center", "update", "sect2",
                     "cat", "cat_loc", "mver", "lver")
        else:
            mkeys = ("master", "center", "subcenter", "update", "sect2",
                     "cat", "cat_int", "cat_loc", "mver", "lver")
        mval = []
        for k in mkeys:
            mval.append(self._meta[k])
        mval.extend((self._meta["datetime"].year, self._meta["datetime"].month,
                     self._meta["datetime"].day, self._meta["datetime"].hour,
                     self._meta["datetime"].minute, self._meta["datetime"].second)
                    )
        if "sect1_local_use" in self._meta:
            mval.append(self._meta["sect1_local_use"])
        json_bufr.append(mval)
        #
        # Section 2
        #
        if self._meta["sect2"]:
            json_bufr.append(self._meta["sect2_data"])
        else:
            json_bufr.append([])
        #
        # Section 3
        #
        sect_buf = []
        sect_buf.extend([self.subsets, self._meta["obs"], self._meta["comp"]])
        mval = []
        for k in self._desc:
            mval.append("%06d" % k)
        sect_buf.append(mval)
        json_bufr.append(sect_buf)
        #
        # Section 4
        #
        stack = []
        if as_array and self.is_compressed:
            def hook_over():
                xpar = stack[-self.subsets:]
                del stack[-self.subsets:]
                for s in range(-self.subsets, 0):
                    stack[s].append(xpar[s])

            def add_empty():
                stack.extend([[] for _ in range(self.subsets)])

            def add_value(value):
                for s in range(-self.subsets, 0):
                    stack[s].append(value[s])
        else:
            def hook_over():
                xpar = stack.pop()
                stack[-1].append(xpar)

            def add_empty():
                stack.append([])

            def add_value(value):
                stack[-1].append(value)

        for report in self.next_subset(as_array and self.is_compressed):
            add_empty()
            rpl_i = [0]
            for descr_entry in report.next_data():
                if descr_entry.mark is not None:
                    mark_el = descr_entry.mark.split(" ")
                    if mark_el[0] in ("RPL", "REP"):
                        if len(mark_el) == 3:
                            # Replication starts
                            add_empty()
                            rpl_i.append(0)
                        elif mark_el[1] == "END":
                            # Replication ends
                            hook_over()
                            hook_over()
                            rpl_i.pop()
                        elif mark_el[1] == "NIL":
                            # No iterations
                            hook_over()
                            rpl_i.pop()
                        else:
                            # For each iteration:
                            if rpl_i[-1]:
                                hook_over()
                            rpl_i[-1] += 1
                            add_empty()
                    elif descr_entry.mark == "BMP DEF":
                        for s in range(-self.subsets if as_array else -1, 0):
                            stack[s].append([[b] for b in descr_entry.value])
                else:
                    if (descr_entry.quality is not None
                            and not isinstance(descr_entry.quality, TabBElem)):
                        add_value(descr_entry.quality)
                    add_value(descr_entry.value)
        json_bufr.append(stack)
        json_bufr.append(["7777"])
        return json_bufr

    def encode(self, json_data, load_tables=True):
        """Encodes the JSON object as BUFR.

        This function creates a BUFR as byte array from the JSON data object.

        The structure of the JSON object is of type "list" and resembles the
        logical structure of a BUFR, where each section itself is a list of
        values in the same order as in a BUFR.

        :param json_data: JSON object.
        :param load_tables: automatically load tables
        :return: BUFR, a byte array object
        :raise BufrDecodeWarning: recoverable error.
        :raise BufrDecodeError: error that stops decoding.
        """
        if len(json_data) != 6:
            raise BufrEncodeError("JSON data has %d sections (not 6)." % len(json_data))
        sect_start = [0] * 6
        bin_data = Blob()
        #
        # Section 0
        #
        sect_i = 0
        sect_start[sect_i], sect_meta = sect.encode_sect0(bin_data, json_data[sect_i][1])
        logger.debug("SECT %d start:%d  %s", sect_i, sect_start[sect_i], sect_meta)
        self._meta.update(sect_meta)
        self.edition = sect_meta['edition']
        if self.edition not in SUPPORTED_BUFR_EDITION:
            raise BufrDecodeError("BUFR edition %d not supported" % self.edition)
        #
        # Section 1
        #
        sect_i += 1
        sect_start[sect_i], sect_meta = sect.encode_sect1(bin_data,
                                                          json_data[sect_i],
                                                          self.edition)
        logger.debug("SECT %d start:%d  %s", sect_i, sect_start[sect_i], sect_meta)
        self._meta.update(sect_meta)
        if load_tables and not self._tables:
            try:
                self._tables = self.load_tables()
            except StandardError or Warning as exc:
                raise exc
        #
        # Section 2
        #
        sect_i += 1
        if self._meta["sect2"]:
            sect_start[sect_i] = sect.encode_sect2(bin_data, json_data[sect_i])
            logger.debug("SECT %d start:%d  %s", sect_i, sect_start[sect_i], json_data[sect_i])
        #
        # Section 3
        #
        sect_i += 1
        sect_start[sect_i], sect_meta = sect.encode_sect3(bin_data,
                                                          json_data[sect_i],
                                                          self.edition)
        logger.debug("SECT %d start:%d  %s", sect_i, sect_start[sect_i], sect_meta)
        self._meta.update(sect_meta)
        self.subsets = sect_meta['subsets']
        self.is_compressed = sect_meta['comp']
        self._desc = sect_meta['descr']
        # Determine if descriptors need recording for back-reference operator
        _, has_backref_oper = get_descr_list(self._tables, self._desc)
        #
        # Section 4
        #
        sect_i += 1
        subset_writer = SubsetWriter(self._tables,
                                     bin_data,
                                     self._desc,
                                     self.is_compressed,
                                     self.subsets,
                                     edition=self.edition,
                                     has_backref=has_backref_oper)
        sect_start[sect_i] = sect.encode_sect4(bin_data,
                                               self.edition)
        logger.debug("SECT %d start:%d", sect_i, sect_start[sect_i])
        subset_writer.process(json_data[sect_i])
        # Pad last octet if needed, align to even octet number if Ed.3
        bin_data.write_align(self.edition == 3)
        #
        # Section 5
        #
        sect_i += 1
        sect_start[sect_i] = sect.encode_sect5(bin_data)
        logger.debug("SECT %d start:%d", sect_i, sect_start[sect_i])
        #
        # Encode section 4 and BUFR size
        #
        sect.encode_sect4_size(bin_data,
                               sect_start[sect_i - 1],
                               sect_start[sect_i])
        sect.encode_bufr_size(bin_data)
        return bin_data.get_bytes()

    def get_blob(self):
        """Return binary array object with the BUFR.

        :return: BUFR
        :rtype: read.Blob
        """
        return self._blob
