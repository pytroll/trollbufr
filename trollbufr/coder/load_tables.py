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
Created on Sep 15, 2016

@author: amaul
'''
import logging
import os
from importlib import import_module
from errors import BufrTableError
from tables import Tables

logger = logging.getLogger("trollbufr")

MODULE_PATTERN = "trollbufr.coder.parse_%s"

BUFR_TABLES_DEFAULT = "%s/.local/share/trollbufr" % (os.getenv('HOME'))

_text_tab_loaded = "Table loaded: '%s'"


class TableCache(object):

    _CACHE_MAX_SIZE = 10

    def __init__(self, base_path, tabf="eccodes"):
        self._base_path = base_path
        self._tabf = tabf
        self._cache = []

    def __str__(self):
        kl = (k for k, _ in self._cache)
        return ", ".join("-".join(str(x) for x in k) for k in kl)

    def load(self, master, center, subcenter, master_vers, local_vers):
        key = (master, center, subcenter, master_vers, local_vers)
        for ckey, tables in self._cache:
            if ckey == key:
                logger.debug("%s from cache", "-".join(str(x) for x in key))
                break
        else:
            tables = load_all(master, center, subcenter, master_vers, local_vers, self._base_path, self._tabf)
            self._cache.append((key, tables))
            if len(self._cache) > TableCache._CACHE_MAX_SIZE:
                self._cache = self._cache[1:]
        return tables


def list_parser():
    return ["eccodes", "libdwd", "bufrdc"]


def load_differ(tables, master, center, subcenter, master_vers, local_vers, base_path, tabf="eccodes"):
    """Load tables, if the versions differ from those already loaded."""
    if tables is None or tables.differs(master, master_vers, local_vers, center, subcenter):
        tables = load_all(master, center, subcenter, master_vers, local_vers, base_path, tabf)
    else:
        logger.debug("Table loading not neccessary")
    return tables


def load_all(master, center, subcenter, master_vers, local_vers, base_path, tabf="eccodes"):
    """Load all given versions of tables"""
    try:
        tparse = import_module(MODULE_PATTERN % tabf)
    except:
        raise BufrTableError("Unknown table parser '%s'!" % tabf)
    if base_path is None:
        base_path = BUFR_TABLES_DEFAULT
    tables = Tables(master, master_vers, local_vers, center, subcenter)
    #
    # Table A (centres)
    try:
        mp, _ = tparse.get_file("A", base_path, master, center, subcenter, master_vers, local_vers)
        tparse.load_tab_a(tables, mp)
        logger.info(_text_tab_loaded, mp)
    except StandardError as e:
        logger.warning(e)
    #
    # Table B (elements)
    try:
        mp, lp = tparse.get_file("B", base_path, master, center, subcenter, master_vers, local_vers)
        # International (master) table
        tparse.load_tab_b(tables, mp)
        logger.info(_text_tab_loaded, mp)
        # Local table
        if local_vers:
            tparse.load_tab_b(tables, lp)
            logger.info(_text_tab_loaded, lp)
    except StandardError as e:
        logger.error(e)
        raise e
    #
    # Table C (operators)
    try:
        mp, _ = tparse.get_file("C", base_path, master, center, subcenter, master_vers, local_vers)
        tparse.load_tab_c(tables, mp)
        logger.info(_text_tab_loaded, mp)
    except StandardError as e:
        logger.warning(e)
    #
    # Table D (sequences)
    try:
        mp, lp = tparse.get_file("D", base_path, master, center, subcenter, master_vers, local_vers)
        # International (master) table
        tparse.load_tab_d(tables, mp)
        logger.info(_text_tab_loaded, mp)
        # Local table
        if local_vers:
            tparse.load_tab_d(tables, lp)
            logger.info(_text_tab_loaded, lp)
    except StandardError as e:
        logger.error(e)
        raise e
    #
    # Table CF (code/flags)
    try:
        mp, lp = tparse.get_file("CF", base_path, master, center, subcenter, master_vers, local_vers)
        # International (master) table
        tparse.load_tab_cf(tables, mp)
        logger.info(_text_tab_loaded, mp)
        # Local table
        if local_vers:
            tparse.load_tab_cf(tables, lp)
            logger.info(_text_tab_loaded, lp)
    except StandardError as er:
        logger.warning(er)

    return tables
