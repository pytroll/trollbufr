#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2016 Alexander Maul
#
# Ported to Py3  09/2018
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
Created on Oct 27, 2016

@author: amaul
'''
import re
from trollbufr.coder import functions as f
from trollbufr.coder.bdata import Blob
from trollbufr.coder.errors import BufrDecodeWarning

import logging
logger = logging.getLogger("trollbufr")

"""This RE matches any Abbreviated Heading Line"""
_re_ahl = re.compile(b"[^A-Z0-9]*?([A-Z]{4}[0-9]{2} [A-Z]{4} [0-9]{6}(?: [ACR][A-Z]{2})?)[^A-Z0-9]+")


def next_bufr(path=None, bin_data=None):
    '''
    Generator:
    Load octets from file, if path is given; otherwise use character-array in bin_data.
    Parse though bin_data for next BUFR.
    If present recognize a bulletins' abbreviated header line (AHL).

    RETURN: (bufr, size, header)
    '''
    if path is not None:
        # Read whole file
        with open(path, "rb") as fh:
            bin_data = fh.read()
            logger.info("FILE %s" % path)
    if bin_data is None:
        raise ValueError("No bin_data!")
    offs = 0
    bufr = None
    size = -1
    header = None
    while offs < len(bin_data):
        # Search for next BUFR
        bstart = offs
        while bin_data[bstart: bstart + 4] != b"BUFR":
            bstart += 1
            if bstart >= len(bin_data) - 30:
                # reached end-of-bin_data
                #raise StopIteration # XXX:
                return
        # At start of file or after previous bufr look for AHL
        m = _re_ahl.search(bin_data[offs:bstart])
        logger.debug("SEARCH AHL : %d - %d %s : %d matches > %s",
                     offs,
                     bstart,
                     bin_data[bstart: bstart + 4],
                     0 if m is None else len(m.groups()),
                     0 if m is None else m.groups()[0]
                     )
        if m is not None:
            header = (m.groups()[0]).decode()
        else:
            header = None
        # Bufr starts here
        offs = bstart
        # Read size of bufr
        offs += 4
        offs, size = f.octets2num(bin_data, offs, 3)
        # Set end of bufr and skip to there
        bend = bstart + size
        offs = bend
        # Check if end is correct
        if bin_data[bend - 4: bend] != b"7777":
            # The bufr is corrupt if section5 is not correct
            logger.error("End '7777' not found")
            raise BufrDecodeWarning("Bufr offset/length error!")
        bufr = Blob(bin_data[bstart: bend])
        logger.debug("LOADED %d B, %d - %d", bend - bstart, bstart, bend)
        # This generator returns one entry
        yield (bufr, size, header)
    #raise StopIteration # XXX:
    return


if __name__ == "__main__":
    import sys
    print(sys.argv)
    for b in next_bufr(path=sys.argv[1]):
        print(b)
