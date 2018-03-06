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
Created on Nov 4, 2016

@author: amaul
'''


class BufrDecodeError(StandardError):
    '''Error class, raised if anything prevents further decoding'''

    def __init__(self, msg):
        super(BufrDecodeError).__init__(type(self))
        self.msg = "BufrDecodeError: %s" % msg

    def __str__(self):
        return self.msg

    def __unicode__(self):
        return self.msg


class BufrDecodeWarning(Warning):
    '''Warning class, raised at recoverable faults'''

    def __init__(self, msg):
        super(BufrDecodeError).__init__(type(self))
        self.msg = "BufrDecodeWarning: %s" % msg

    def __str__(self):
        return self.msg

    def __unicode__(self):
        return self.msg


class BufrEncodeError(StandardError):
    '''Error class, raised if anything prevents further encoding'''

    def __init__(self, msg):
        super(BufrEncodeError).__init__(type(self))
        self.msg = "BufrEncodeError: %s" % msg

    def __str__(self):
        return self.msg

    def __unicode__(self):
        return self.msg


class BufrTableWarning(Warning):
    '''Warning class, raised at recoverable faults'''

    def __init__(self, msg):
        super(BufrTableWarning).__init__(type(self))
        self.msg = "BufrTableWarning: %s" % msg

    def __str__(self):
        return self.msg

    def __unicode__(self):
        return self.msg


class BufrTableError(StandardError):
    '''Error class, raised if anything prevents further decoding'''

    def __init__(self, msg):
        super(BufrTableError).__init__(type(self))
        self.msg = "BufrTableError: %s" % msg

    def __str__(self):
        return self.msg

    def __unicode__(self):
        return self.msg
