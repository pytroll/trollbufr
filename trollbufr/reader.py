#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2016,2017 Alexander Maul
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
trollbufr.reader
================
Command-line interface, reads BUFR (with abbreviated heading line,
if present) from file(s) and writes human-readable to stdout.
'''
import sys
import os
from argparse import ArgumentParser
from argparse import RawDescriptionHelpFormatter
from version import __version__
from bufr import Bufr
import load_file
import tab.load_tables

import logging
logger = logging.getLogger("trollbufr")


def read_bufr_data(args):
    bufr_files = args.bufr
    bufr = Bufr(args.tables_type, args.tables_path)
    for fn in bufr_files:
        print "FILE\t%s" % fn
        i = 0
        for blob, size, header in load_file.next_bufr(fn):
            if args.bulletin is not None and i != args.bulletin:
                i += 1
                continue
            print "BUFR\t#%d (%d B)" % (i, size)
            i += 1
            print "HEADER\t%s" % header
            try:
                bufr.decode(blob, tables=False)
                tabl = bufr.load_tables()
                print "META:\n%s" % bufr.get_meta_str()
                for report in bufr.next_subset():
                    print "SUBSET\t#%d/%d" % report.subs_num
                    if args.sparse:
                        for k, m, (v, q) in report.next_data():
                            if m is not None:
                                print "   ", m
                                continue
                            if v is None:
                                print "%06d: ///" % (k)
                            elif q is not None:
                                print "%06d: %s (%s)" % (k, str(v), q)
                            else:
                                print "%06d: %s" % (k, str(v))
                    else:
                        for k, m, (v, q) in report.next_data():
                            if m is not None:
                                print "  ", m
                                continue
                            kn, ku = tabl.lookup_elem(k)
                            if "table" in ku:
                                if v is None:
                                    print "%06d %-40s = Missing value" % (k, kn)
                                else:
                                    v = tabl.lookup_codeflag(k, v)
                                    print "%06d %-40s = %s" % (k, kn, str(v))
                            else:
                                if ku == "CCITT IA5" or ku == "Numeric":
                                    ku = ""
                                if v is None:
                                    print "%06d %-40s = /// %s" % (k, kn, ku)
                                elif q is not None:
                                    print "%06d %-40s = %s %s (%s)" % (k, kn, str(v), ku, q)
                                else:
                                    print "%06d %-40s = %s %s" % (k, kn, str(v), ku)
            except StandardError as e:
                print "ERROR\t%s" % e
                if logger.isEnabledFor(logging.DEBUG):
                    logger.exception(e)


def read_bufr_desc(args):
    bufr_files = args.bufr
    for fn in bufr_files:
        print "FILE\t%s" % fn
        i = 0
        for blob, size, header in load_file.next_bufr(fn):
            if args.bulletin is not None and i != args.bulletin:
                i += 1
                continue
            print "BUFR\t#%d (%d B)" % (i, size)
            i += 1
            print "HEADER\t%s" % header
            try:
                bufr = Bufr(args.tables_type, args.tables_path)
                bufr.decode(blob, tables=(not args.sparse))
                print "META\n%s" % bufr.get_meta_str()
                if args.sparse:
                    d = bufr.get_descr_short()
                else:
                    d = bufr.get_descr_full()
                print "DESC :\n%s" % "\n".join(d)
            except StandardError as e:
                print "ERROR\t%s" % e
                if logger.isEnabledFor(logging.DEBUG):
                    logger.exception(e)


def run(argv=None):
    '''Command line options.'''
    if argv is None:
        argv = sys.argv
    else:
        sys.argv.extend(argv)
    program_version = __version__
    try:
        # Setup argument parser
        parser = ArgumentParser(description=__import__('__main__').__doc__,
                                formatter_class=RawDescriptionHelpFormatter
                                )
        parser.add_argument("-v", "--verbose", dest="verbose",
                            action="count",
                            help="set verbosity level [default: 0]"
                            )
        parser.add_argument("-s", "--sparse", dest="sparse",
                            action="store_true",
                            help="sparse output, no tables loaded"
                            )
        group_op = parser.add_argument_group(title="operator",
                                             description="what to do (at least one required)"
                                             )
        group_op.add_argument("-r", "--read", dest="reader",
                              action="store_true",
                              help="print data"
                              )
        group_op.add_argument("-d", "--desc", dest="desc",
                              action="store_true",
                              help="print info/descriptor"
                              )
        group_op.add_argument("-b", "--bulletin", dest="bulletin",
                              default=None,
                              type=int,
                              metavar="N",
                              help="decode only bulletin #N in file (starts with '0')"
                              )
        group_tab = parser.add_argument_group(title="table setting")
        group_tab.add_argument("-t", "--tables_path",
                               default=os.getenv("BUFR_TABLES"),
                               help="path to tables, if not set in $BUFR_TABLES",
                               metavar="path"
                               )
        group_tab.add_argument("-T", "--tables_type",
                               default=tab.load_tables.list_parser()[0],
                               choices=tab.load_tables.list_parser(),
                               help="type of table format [%s], default: %s" % (
                                    "|".join(tab.load_tables.list_parser()),
                                   tab.load_tables.list_parser()[0]
                               ),
                               metavar="name"
                               )
        parser.add_argument('-V', '--version',
                            action='version',
                            version="pybufr %s" % program_version
                            )
        parser.add_argument(dest="bufr",
                            help="file(s) with BUFR content",
                            metavar="file",
                            nargs='+'
                            )
        # Process arguments
        args = parser.parse_args()

        handler = logging.StreamHandler()
        log_formater_line = "[%(levelname)s] %(message)s"
        if not args.verbose:
            loglevel = logging.WARN
        else:
            if args.verbose == 1:
                loglevel = logging.INFO
            elif args.verbose >= 2:
                loglevel = logging.DEBUG
                log_formater_line = "[%(levelname)s: %(module)s:%(lineno)d] %(message)s"
        handler.setFormatter(logging.Formatter(log_formater_line))
        handler.setLevel(loglevel)
        logging.getLogger('').setLevel(loglevel)
        logging.getLogger('').addHandler(handler)

        logger.debug(args)
        if args.tables_path is None:
            sys.stderr.write("No path to tables given!")
            return 1
        if not (args.desc or args.reader):
            sys.stderr.write("Unknown operation!")
            return 1

        if args.desc:
            read_bufr_desc(args)
        if args.reader:
            read_bufr_data(args)

    except KeyboardInterrupt:
        return 0
    except StandardError as e:
        if logger.isEnabledFor(logging.DEBUG):
            logger.exception(e)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(run())
