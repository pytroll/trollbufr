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
from __future__ import print_function

import sys
import os
from argparse import ArgumentParser
from argparse import RawDescriptionHelpFormatter
from version import __version__
from bufr import Bufr
from coder.tables import TabBelem
import load_file
import coder.load_tables

import logging
logger = logging.getLogger("trollbufr")


def read_bufr_data(args):
    bufr_files = args.bufr
    bufr = Bufr(args.tables_type, args.tables_path)
    for fn in bufr_files:
        print ("FILE\t%s" % fn)
        i = 0
        for blob, size, header in load_file.next_bufr(fn):
            if args.bulletin is not None and i != args.bulletin:
                i += 1
                continue
            print("BUFR\t#%d (%d B)" % (i, size))
            i += 1
            print("HEADER\t%s" % header)
            try:
                bufr.decode(blob, load_tables=False)
                tabl = bufr.load_tables()
                print("META:\n%s" % bufr.get_meta_str())
                for report in bufr.next_subset():
                    print("SUBSET\t#%d/%d" % report.subs_num)
                    if args.sparse:
                        for descr_entry in report.next_data():
                            if descr_entry.mark is not None:
                                print("  ", descr_entry.mark, end="")
                                if descr_entry.value:
                                    print(" ", "".join(str(x) for x in descr_entry.value), end="")
                                print()
                                continue
                            if descr_entry.value is None:
                                print("%06d: ///" % (descr_entry.descr))
                            elif descr_entry.quality is not None:
                                print("%06d: %s (%s)" % (descr_entry.descr,
                                                         str(descr_entry.value),
                                                         descr_entry.quality))
                            else:
                                print("%06d: %s" % (descr_entry.descr,
                                                    str(descr_entry.value)))
                    else:
                        for descr_entry in report.next_data():
                            if descr_entry.mark is not None:
                                print("  ", descr_entry.mark, end="")
                                if descr_entry.value:
                                    print(" ",
                                          "".join(str(x) for x in descr_entry.value),
                                          end="")
                                print()
                                continue
                            d_name, d_unit, d_typ = tabl.lookup_elem(descr_entry.descr)
                            if d_typ in (TabBelem.CODE, TabBelem.FLAG):
                                if descr_entry.value is None:
                                    print("%06d %-40s = Missing value"
                                          % (descr_entry.descr, d_name))
                                else:
                                    v = tabl.lookup_codeflag(descr_entry.descr,
                                                             descr_entry.value)
                                    print("%06d %-40s = %s"
                                          % (descr_entry.descr,
                                             d_name,
                                             str(v)))
                            else:
                                if d_unit in ("CCITT IA5", "Numeric"):
                                    d_unit = ""
                                if descr_entry.value is None:
                                    print("%06d %-40s = /// %s"
                                          % (descr_entry.descr,
                                             d_name, d_unit))
                                elif descr_entry.quality is not None:
                                    print("%06d %-40s = %s %s (%s)"
                                          % (descr_entry.descr,
                                             d_name,
                                             str(descr_entry.value),
                                             d_unit,
                                             descr_entry.quality))
                                else:
                                    print("%06d %-40s = %s %s"
                                          % (descr_entry.descr,
                                             d_name,
                                             str(descr_entry.value),
                                             d_unit))
            except StandardError as e:
                print("ERROR\t%s" % e)
                if logger.isEnabledFor(logging.DEBUG):
                    logger.exception(e)
                else:
                    logger.warning(e)


def get_bufr_json(args):
    bufr_files = args.bufr
    bufr = Bufr(args.tables_type, args.tables_path)
    json_data = []
    bufr_i = -1
    for fn in bufr_files:
        for blob, _, header in load_file.next_bufr(fn):
            bufr_i += 1
            if args.bulletin is not None and bufr_i != args.bulletin:
                continue
            try:
                bufr.decode(blob, True)
                # Section 0
                json_data.append(header)
                json_data.append(["BUFR", bufr._meta["edition"]])
                # Section 1
                if bufr._meta["edition"] == 3:
                    mkeys = ["master", "subcenter", "center", "update", "sect2",
                             "cat", "cat_loc", "mver", "lver", ]
                else:
                    mkeys = ["master", "center", "subcenter", "update", "sect2",
                             "cat", "cat_int", "cat_loc", "mver", "lver", ]
                mval = []
                for k in mkeys:
                    mval.append(bufr._meta[k])
                mval.extend((bufr._meta["datetime"].year, bufr._meta["datetime"].month,
                             bufr._meta["datetime"].day, bufr._meta["datetime"].hour,
                             bufr._meta["datetime"].minute, bufr._meta["datetime"].second)
                            )
                json_data.append(mval)
                # Section 3
                sect_buf = []
                sect_buf.extend([bufr._subsets, bufr._meta["obs"], bufr._meta["comp"]])
                mval = []
                for k in bufr._desc:
                    mval.append("%06d" % k)
                sect_buf.append(mval)
                json_data.append(sect_buf)
                # Section 4
                stack = []
                for report in bufr.next_subset():
                    stack.append([])
                    rpl_i = 0
                    for descr_entry in report.next_data():
                        if descr_entry.mark is not None:
                            mark_el = descr_entry.mark.split(" ")
                            if mark_el[0] in ("RPL", "REP"):
                                if len(mark_el) == 3:
                                    # Replication starts
                                    stack.append([])
                                    rpl_i = 0
                                elif mark_el[1] == "END":
                                    # Replication ends
                                    xpar = stack.pop()
                                    stack[-1].append(xpar)
                                    xpar = stack.pop()
                                    stack[-1].append(xpar)
                                elif mark_el[1] == "NIL":
                                    # No iterations
                                    xpar = stack.pop()
                                    stack[-1].append(xpar)
                                else:
                                    # For each iteration:
                                    if rpl_i:
                                        xpar = stack.pop()
                                        stack[-1].append(xpar)
                                    rpl_i += 1
                                    stack.append([])
                            elif mark_el[0] == "BMP":
                                stack[-1].append(descr_entry.value)
                        else:
                            if isinstance(descr_entry.quality, (int, float)):
                                stack[-1].append(descr_entry.quality)
                            stack[-1].append(descr_entry.value)
                json_data.append(stack)
                json_data.append(["7777"])
            except StandardError as e:
                logger.exception(e)
    return json_data


def read_bufr_desc(args):
    bufr_files = args.bufr
    for fn in bufr_files:
        print("FILE\t%s" % fn)
        i = 0
        for blob, size, header in load_file.next_bufr(fn):
            if args.bulletin is not None and i != args.bulletin:
                i += 1
                continue
            print("BUFR\t#%d (%d B)" % (i, size))
            i += 1
            print("HEADER\t%s" % header)
            try:
                bufr = Bufr(args.tables_type, args.tables_path)
                bufr.decode(blob, load_tables=(not args.sparse))
                print("META\n%s" % bufr.get_meta_str())
                if args.sparse:
                    d = bufr.get_descr_short()
                else:
                    d = bufr.get_descr_full()
                print("DESC :\n%s" % "\n".join(d))
            except StandardError as e:
                print("ERROR\t%s" % e)
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
        parser.add_argument('-V', '--version',
                            action='version',
                            version="pybufr %s" % program_version
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
        group_op.add_argument("-j", "--json-dump", dest="json_dump",
                              metavar="file",
                              help="dump data in JSON format"
                              )
        group_tab = parser.add_argument_group(title="table setting")
        group_tab.add_argument("-t", "--tables_path",
                               default=os.getenv("BUFR_TABLES"),
                               help="path to tables, if not set in $BUFR_TABLES",
                               metavar="path"
                               )
        group_tab.add_argument("-T", "--tables_type",
                               default=coder.load_tables.list_parser()[0],
                               choices=coder.load_tables.list_parser(),
                               help="type of table format [%s], default: %s" % (
                                    "|".join(coder.load_tables.list_parser()),
                                   coder.load_tables.list_parser()[0]
                               ),
                               metavar="name"
                               )
        parser.add_argument("-b", "--bulletin", dest="bulletin",
                            default=None,
                            type=int,
                            metavar="N",
                            help="decode only bulletin #N in file (starts with '0')"
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
        if not (args.desc or args.reader or args.json_dump):
            sys.stderr.write("Unknown operation!")
            return 1

        PROFILE = True
        if PROFILE:
            import cProfile
            import pstats
            pr = cProfile.Profile()
            pr.enable()

        if args.desc:
            read_bufr_desc(args)
        if args.reader:
            read_bufr_data(args)
        if args.json_dump:
            foo = get_bufr_json(args)
            import json
            with open(args.json_dump, "wb") as fh_out:
                if args.sparse:
                    json.dump(foo, fh_out)
                else:
                    json.dump(foo, fh_out, indent=3, separators=(',', ': '))

        if PROFILE:
            pr.disable()
            sortby = 'cumulative'
            ps = pstats.Stats(pr, stream=sys.stderr).sort_stats(sortby)
            ps.print_stats()

    except KeyboardInterrupt:
        return 0
    except StandardError as e:
        if logger.isEnabledFor(logging.DEBUG):
            logger.exception(e)
        else:
            logger.warning(e)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(run())
