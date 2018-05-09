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
from argparse import ArgumentParser, RawDescriptionHelpFormatter
from version import __version__
from bufr import Bufr
from coder.bufr_types import TabBType
import load_file
import coder.load_tables

import logging
logger = logging.getLogger("trollbufr")


def read_bufr_data(args):
    """Read BUFR(s), decode data section and write to file-handle.

    Depending on command argument "--array", either process the subsets in
    sequence, which is ideal for un-compressed BUFR, or process each descriptor
    per all subsets at once, which improves performance for compressed BUFR.
    """
    try:
        fh_out = open(args.out_file, "wb")
    except:
        fh_out = sys.stdout
    bufr = Bufr(args.tables_type, args.tables_path)
    for fn_in in args.in_file:
        print("FILE\t%s" % os.path.basename(fn_in), file=fh_out)
        i = 0
        for blob, size, header in load_file.next_bufr(fn_in):
            if args.bulletin is not None and i != args.bulletin:
                i += 1
                continue
            print("BUFR\t#%d (%d B)" % (i, size), file=fh_out)
            i += 1
            print("HEADER\t%s" % header, file=fh_out)
            try:
                bufr.decode_meta(blob, load_tables=False)
                tabl = bufr.load_tables()
                print("META:\n%s" % bufr.get_meta_str(), file=fh_out)
                for report in bufr.next_subset(args.array and bufr.is_compressed):
                    print("SUBSET\t#%d/%d" % report.subs_num, file=fh_out)
                    if args.sparse or (args.array and bufr.is_compressed):
                        for descr_entry in report.next_data():
                            if descr_entry.mark is not None:
                                print("  ", descr_entry.mark, end="", file=fh_out)
                                if descr_entry.value:
                                    print("", "".join(str(x) for x in descr_entry.value), end="", file=fh_out)
                                print(file=fh_out)
                                continue
                            if descr_entry.value is None:
                                print("%06d: ///" % (descr_entry.descr), file=fh_out)
                            elif descr_entry.quality is not None:
                                print("%06d: %s (%s)" % (descr_entry.descr,
                                                         str(descr_entry.value),
                                                         descr_entry.quality), file=fh_out)
                            else:
                                print("%06d: %s" % (descr_entry.descr,
                                                    str(descr_entry.value)), file=fh_out)
                    else:
                        for descr_entry in report.next_data():
                            if descr_entry.mark is not None:
                                print("  ", descr_entry.mark, end="", file=fh_out)
                                if descr_entry.value:
                                    try:
                                        print("",
                                              "".join(str(x) for x in descr_entry.value),
                                              end="", file=fh_out)
                                    except StandardError as e:
                                        logger.exception("%s", descr_entry)
                                        raise e
                                print(file=fh_out)
                                continue
                            d_name, d_unit, d_typ = tabl.lookup_elem(descr_entry.descr)
                            if d_typ in (TabBType.CODE, TabBType.FLAG):
                                if descr_entry.value is None:
                                    print("%06d %-40s = Missing value"
                                          % (descr_entry.descr, d_name), file=fh_out)
                                else:
                                    v = tabl.lookup_codeflag(descr_entry.descr,
                                                             descr_entry.value)
                                    print("%06d %-40s = %s"
                                          % (descr_entry.descr,
                                             d_name,
                                             str(v)), file=fh_out)
                            else:
                                if d_unit in ("CCITT IA5", "Numeric"):
                                    d_unit = ""
                                if descr_entry.value is None:
                                    print("%06d %-40s = /// %s"
                                          % (descr_entry.descr,
                                             d_name, d_unit), file=fh_out)
                                elif descr_entry.quality is not None:
                                    print("%06d %-40s = %s %s (%s)"
                                          % (descr_entry.descr,
                                             d_name,
                                             str(descr_entry.value),
                                             d_unit,
                                             descr_entry.quality), file=fh_out)
                                else:
                                    print("%06d %-40s = %s %s"
                                          % (descr_entry.descr,
                                             d_name,
                                             str(descr_entry.value),
                                             d_unit), file=fh_out)
            except StandardError as e:
                print("ERROR\t%s" % e, file=fh_out)
                if logger.isEnabledFor(logging.DEBUG):
                    logger.exception(e)
                else:
                    logger.warning(e)
    if fh_out is not sys.stdout:
        fh_out.close()


def read_bufr_to_json(args):
    """Read and decode BUFR, write as JSON formatted file.
    """
    bufr = Bufr(args.tables_type, args.tables_path)
    json_data = []
    bufr_i = -1
    for fn_in in args.in_file:
        for blob, _, header in load_file.next_bufr(fn_in):
            bufr_i += 1
            if args.bulletin is not None and bufr_i != args.bulletin:
                continue
            json_data.append({"heading": header,
                              "file": os.path.basename(fn_in),
                              "index": bufr_i,
                              })
            try:
                json_bufr = bufr.decode(blob,
                                        load_tables=True,
                                        as_array=args.array)
            except StandardError as e:
                logger.error(e, exc_info=1 and logger.isEnabledFor(logging.DEBUG))
                json_data[-1]["error"] = str(e)
            else:
                json_data[-1]["bufr"] = json_bufr
    import json
    out_fh = open(args.out_file, "wb") or sys.stdout
    with out_fh as fh_out:
        if args.sparse:
            json.dump(json_data, fh_out)
        else:
            json.dump(json_data, fh_out, indent=3, separators=(',', ': '))


def read_bufr_desc(args):
    """Read BUFR(s), decode meta-data and descriptor list, write to file-handle.
    """
    try:
        fh_out = open(args.out_file, "wb")
    except:
        fh_out = sys.stdout
    for fn_in in args.in_file:
        print("FILE\t%s" % os.path.basename(fn_in), file=fh_out)
        i = 0
        for blob, size, header in load_file.next_bufr(fn_in):
            if args.bulletin is not None and i != args.bulletin:
                i += 1
                continue
            print("BUFR\t#%d (%d B)" % (i, size), file=fh_out)
            i += 1
            print("HEADER\t%s" % header, file=fh_out)
            try:
                bufr = Bufr(args.tables_type, args.tables_path)
                bufr.decode_meta(blob, load_tables=(not args.sparse))
                print("META\n%s" % bufr.get_meta_str(), file=fh_out)
                if args.sparse:
                    d = bufr.get_descr_short()
                else:
                    d = bufr.get_descr_full()
                print("DESC :\n%s" % "\n".join(d), file=fh_out)
            except StandardError as e:
                print("ERROR\t%s" % e, file=fh_out)
                if logger.isEnabledFor(logging.DEBUG):
                    logger.exception(e)
    if fh_out is not sys.stdout:
        fh_out.close()


def write_bufr(args):
    """Read JSON file, encode as BUFR and write to file-handle.
    """
    import json
    try:
        fh_out = open(args.out_file, "wb")
    except:
        fh_out = sys.stdout
    multi_bul = False
    for fn_in in args.in_file:
        with open(fn_in, "rb") as fh_in:
            json_data = json.load(fh_in)
        for json_data_msg in json_data:
            if not "bufr" in json_data_msg:
                continue
            bufr = Bufr(tab_fmt=args.tables_type,
                        tab_path=args.tables_path)
            bin_data = bufr.encode(json_data_msg["bufr"],
                                   load_tables=True)
            if json_data_msg["heading"] is not None:
                multi_bul and print("\r\r\n\r\r\n", end="", file=fh_out)
                print("%s\r\r" % json_data_msg["heading"], file=fh_out)
            print(bin_data, end="", file=fh_out)
            multi_bul = True
    if fh_out is not sys.stdout:
        fh_out.close()


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
        parser.add_argument("-a", "--array", dest="array",
                            action="store_true",
                            help="values as array (compressed BUFR only!)"
                            )
        parser.add_argument("-o", "--output", dest="out_file",
                            metavar="file",
                            help="write to file instead STDOUT"
                            )
        group_op = parser.add_argument_group(title="operator",
                                             description="what to do (at least one required)"
                                             )
        group_op.add_argument("-m", "--meta", dest="desc",
                              action="store_true",
                              help="print info/descriptor"
                              )
        group_op.add_argument("-d", "--decode", dest="reader",
                              action="store_true",
                              help="decode and print data"
                              )
        group_op.add_argument("-j", "--decode-json", dest="json_dump",
                              action="store_true",
                              help="decode and dump data in JSON format"
                              )
        group_op.add_argument("-e", "--encode", dest="json_encode",
                              action="store_true",
                              help="encode data from JSON file as BUFR"
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
        parser.add_argument(dest="in_file",
                            help="file(s) with BUFR or JSON content",
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
        if not (args.desc or args.reader or args.json_dump or args.json_encode):
            sys.stderr.write("Unknown operation!")
            return 1

        PROFILE = False
        if PROFILE:
            import cProfile
            import pstats
            pr = cProfile.Profile()
            pr.enable()

        if args.desc:
            read_bufr_desc(args)
        if args.reader:
            read_bufr_data(args)
        elif args.json_dump:
            read_bufr_to_json(args)
        elif args.json_encode:
            write_bufr(args)

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
