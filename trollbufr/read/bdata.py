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
'''
Class around the BUFR byte string.

Created on Nov 17, 2016

@author: amaul
'''
import logging
logger = logging.getLogger("trollbufr")
from errors import BufrDecodeError

class Blob(object):
    _data = None
    _point = -1
    _bitcons = -1

    def __init__(self, data):
        """Initialising the class with an octet array (type string)"""
        self._data = data
        self.reset()

    def __str__(self):
        return "%dB %d/%d" % (len(self._data), self._point, self._bitcons)

    def __len__(self):
        return len(self._data)

    def __getitem__(self, x):
        if isinstance(x, tuple):
            return self._data[x[0]:x[1]]
        else:
            return self._data[x]

    def get_point(self):
        return self._point

    def set_point(self, point):
        self._point = point

    def get_bitcons(self):
        return self._bitcons

    def set_bitcons(self, consumed):
        if consumed == 8:
            consumed = 0
            self._point += 1
        self._bitcons = consumed

    p = property(get_point, set_point)
    bc = property(get_bitcons, set_bitcons)

    def reset(self, x=0):
        """Reset internal pointer to position x or start"""
        self._point = x
        self._bitcons = 0

    def slice(self, start=0, stop=-1):
        return self._data[start:stop]

    def get_octets(self, count=1):
        a = self._point
        self._point += count
        if self._point > len(self._data):
            self._point = len(self._data)
        b = self._point
        return self._data[a:b]

    def skip_bits(self, width):
        """Skip width bits.
        
        Move internal pointer when some bits don't need processing.
        :return: Void.
        """
        if not width:
            return
        self._point += (self._bitcons + width) // 8
        self._bitcons = (self._bitcons + width) % 8

    def get_bits(self, width):
        """Read width bits from internal buffer.
        
        :return: character buffer, which needs further decoding.
        """
        n = 0
        x = 0
        while width:
            p = ord(self._data[self._point])
            if self._bitcons + width <= 8:
                x = (p & (0xFF >> self._bitcons)) >> (8 - self._bitcons - width)
                n |= x
                self._bitcons += width
                if self._bitcons == 8:
                    self._bitcons = 0
                    self._point += 1
                return n
            elif self._bitcons + width > 8:
                x = p & (0xFF >> self._bitcons)
                n |= x
                width -= 8 - self._bitcons
                if width > 8:
                    n <<= 8
                else:
                    n <<= width
                self._bitcons = 0
                self._point += 1
        # Reaching this line shouldn't happen
        raise BufrDecodeError()

