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
"""
Class around the BUFR byte string.

Created on Nov 17, 2016

@author: amaul
"""
from bitstring import Bits, BitStream
import six


class Blob(object):

    _data = None

    def __init__(self, bin_data=None):
        """Initialising the class with an octet array (type string)"""
        if bin_data is None:
            self._data = BitStream()
        else:
            self._data = BitStream(bytes=bin_data)
        self.reset()

    def __str__(self):
        return "%dB %d/%d" % (len(self._data) / 8, self._data.pos // 8, self._data.pos % 8)

    def __len__(self):
        return len(self._data)

    def __getitem__(self, x):
        if isinstance(x, tuple):
            return self._data[x[0]:x[1]]
        else:
            return self._data[x]

    def reset(self, x=0):
        """Reset internal pointer to position x or start"""
        self._data.pos = x * 8

    def get_bytes(self):
        return self._data.bytes

    def get_point(self):
        return self._data.pos // 8

    def set_point(self, point):
        self._data.pos = point * 8

    def get_bitcons(self):
        return self._data.pos % 8

    def set_bitcons(self, consumed):
        self._data.pos += consumed

    p = property(get_point, set_point)
    bc = property(get_bitcons, set_bitcons)

    def read(self, fmt):
        return self._data.read(fmt)

    def readlist(self, fmt):
        return self._data.readlist(fmt)

    def writelist(self, fmt, json_data):
        self._data += Bits(fmt.format(*json_data))

    def read_align(self, even=False):
        p = self._data.pos
        self._data.bytealign()
        if even and (self._data.pos / 8) & 1:
            self._data.pos += 8
        return self._data.pos - p

    def write_align(self, even=False):
        width = (8 - len(self._data) % 8) & 7
        if even and (len(self._data) / 8) & 1:
            width += 8
        self._data += ("uint:{}={}").format(width, 0)

    def read_skip(self, width):
        """Skip width bits.

        Move internal pointer when some bits don't need processing.
        :return: Void.
        """
        # self._data.read("pad:%d" % width)
        self._data.pos += width

    def write_skip(self, width):
        """Skip width bits.

        Move internal pointer when some bits don't need processing.
        :return: Void.
        """
        self._data += ("uintbe:{}={}" if not width & 7 else
                       "uint:{}={}").format(width, 0)

    def read_bytes(self, width=1):
        return self._data.read("bytes:%d" % width)

    def read_bits(self, width):
        """Read width bits from internal buffer.

        :return: character buffer, which needs further decoding.
        """
        if width & 7:
            return self._data.read("uint:%d" % width)
        else:
            return self._data.read("uintbe:%d" % width)

    def write_bytes(self, value, width=None):
        """
        :param value: character array (String)
        :param width: the string's width in bits, not octets.
        """
        if isinstance(value, six.text_type):
            value = value.encode("latin-1")
        value_len = len(value)
        if width is None:
            width = value_len
        else:
            width //= 8
            if value_len > width:
                value = value[:width]
            elif value_len < width:
                value += b" " * (width - value_len)
        self._data += Bits(bytes=value)
        return len(self._data)

    def write_uint(self, value, width):
        value = int(value)
        self._data += ("uintbe:{}={}" if width % 8 == 0 else
                       "uint:{}={}").format(width, value)
        return len(self._data)

    def set_uint(self, value, width, bitpos):
        if width // 8 == 0:
            bins = Bits(uint=value, length=width)
        else:
            bins = Bits(uintbe=value, length=24)
        self._data[bitpos: bitpos + width] = bins
