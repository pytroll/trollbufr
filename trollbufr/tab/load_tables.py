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

MODULE_PATTERN = "trollbufr.tab.parse_%s"

BUFR_TABLES_DEFAULT = "%s/.local/share/trollbufr" % (os.getenv('HOME'))

_text_tab_loaded = "Table loaded: '%s'"


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


def test_b():
    base_path = "tables"
    master = 0
    center = 78
    subcenter = 0
    master_vers = 24
    local_vers = 8

    _tabformat_eccodes = "eccodes"
    _tabformat_libdwd = "libdwd"
    tabf = _tabformat_eccodes
    t = load_all(master, center, subcenter, master_vers, local_vers, base_path, tabf)
    print len(t.tab_b), len(t.tab_c), len(t.tab_d), len(t.tab_cf), t

    print "TAB_B"
    for k, v in t.tab_b.items()[0:10]:
        print k, v
    print "TAB_C"
    for k, v in t.tab_c.items()[0:10]:
        print k, v
    print "TAB_D"
    for k, v in t.tab_d.items()[0:10]:
        print k, v
    print "TAB_CF"
    for k, v in t.tab_cf.items()[0:10]:
        print k, v

    tabf = _tabformat_libdwd
    t = load_all(master, center, subcenter, master_vers, local_vers, base_path, tabf)
    print len(t.tab_b), len(t.tab_c), len(t.tab_d), len(t.tab_cf), t


def test_a():
    base_path = "%s/BUFRtables" % (os.getenv('HOME'))
    master = 0
    center = 78
    subcenter = 0
    master_vers = 24
    local_vers = 8

    for tabf in list_parser():
        tparse = import_module("tab.%s" % list_parser())
        tables = Tables(master, master_vers, local_vers, center, subcenter)
        mp, lp = tparse.get_file(tabf, "B", base_path, master, center, subcenter, master_vers, local_vers)
        print mp, lp, os.path.exists(mp), os.path.exists(lp)
        tparse.load_tab_b(tables, tabf, mp)
        tparse.load_tab_b(tables, tabf, lp)
        mp, lp = tparse.get_file(tabf, "C", base_path, master, center, subcenter, master_vers, local_vers)
        print mp, lp, os.path.exists(mp), os.path.exists(lp)
        tparse.load_tab_c(tables, tabf, mp)
        tparse.load_tab_c(tables, tabf, lp)
        mp, lp = tparse.get_file(tabf, "CF", base_path, master, center, subcenter, master_vers, local_vers)
        print mp, lp, os.path.exists(mp), os.path.exists(lp)
        tparse.load_tab_cf(tables, tabf, mp)
        tparse.load_tab_cf(tables, tabf, lp)
        mp, lp = tparse.get_file(tabf, "D", base_path, master, center, subcenter, master_vers, local_vers)
        print mp, lp, os.path.exists(mp), os.path.exists(lp)
        tparse.load_tab_d(tables, tabf, mp)
        tparse.load_tab_d(tables, tabf, lp)

    import pickle
    with open("table_%s_%03d_%03d-%03d_%03d.dat" % ('a', master_vers, center, subcenter, local_vers), "wb") as ph:
        pickle.dump(tables.tab_a, ph)
    with open("table_%s_%03d_%03d-%03d_%03d.dat" % ('b', master_vers, center, subcenter, local_vers), "wb") as ph:
        pickle.dump(tables.tab_b, ph)
    with open("table_%s_%03d_%03d-%03d_%03d.dat" % ('c', master_vers, center, subcenter, local_vers), "wb") as ph:
        pickle.dump(tables.tab_c, ph)
    with open("table_%s_%03d_%03d-%03d_%03d.dat" % ('d', master_vers, center, subcenter, local_vers), "wb") as ph:
        pickle.dump(tables.tab_d, ph)
    with open("table_%s_%03d_%03d-%03d_%03d.dat" % ('cf', master_vers, center, subcenter, local_vers), "wb") as ph:
        pickle.dump(tables.tab_cf, ph)


if __name__ == "__main__":
    test_b()
    pass
