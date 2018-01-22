#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2016,2018 Alexander Maul
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
# along with this program.  If not, see <http://www.gnu.org/licenses//gpl.html>.
"""
TrollBUFR - table update.
"""
import sys
import os

import urllib2
from argparse import ArgumentParser
from argparse import RawDescriptionHelpFormatter

import logging
logger = logging.getLogger("trollbufr")

__version__ = "0.1.0"

E_OK = 0
E_ARG = 1
E_ERR = 2


def arg_parser():
    program_name = os.path.basename(sys.argv[0])
    # Setup argument parser
    parser = ArgumentParser(description=__import__('__main__').__doc__,
                            formatter_class=RawDescriptionHelpFormatter
                            )
    parser.add_argument("-v", "--verbose",
                        dest="verbose",
                        action="count",
                        help="set verbosity level [default: %(default)s]"
                        )
    parser.add_argument('-V', '--version',
                        action='version',
                        version="%s %s" % (program_name, __version__)
                        )
    parser.add_argument("-t", "--tables-path",
                        default=os.getenv("BUFR_TABLES"),
                        help="path to tables, if not set in $BUFR_TABLES",
                        metavar="PATH"
                        )
    parser.add_argument("-F", "--url-file",
                        help="File with URL list",
                        metavar="FILE",
                        )
    parser.add_argument("-U", "--url",
                        help="URL for table archive",
                        metavar="URL",
                        nargs="+"
                        )
    # Process arguments
    args = parser.parse_args()
    # Setup logger
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
    # Return arguments
    return args


def run(argv=None):
    """Command line options."""
    if argv is None:
        argv = sys.argv
    else:
        sys.argv.extend(argv)
    args = arg_parser()
    if args.url:
        url_list = args.url
        logger.debug("URLs from args")
    elif args.url_file:
        url_list = []
        with open(args.url_file, "r") as fh_url:
            for line in fh_url:
                url_list.append(line.strip())
    else:
        sys.stderr.write("URL or URL-file missing!\n")
        return 1
    try:
        logger.debug("Sources: %s", url_list)
        logger.debug("Destination: %s", args.tables_path)
        for url in url_list:
            arc_name = url.split("/")[-1]
            arc_dest = os.path.join(args.tables_path, arc_name)
            if not os.path.exists(args.tables_path):
                logger.warning("Path does not exist: %s", args.tables_path)
                return E_ARG
            with open(arc_dest, "w") as dest:
                logger.info("Download %s", url)
                response = urllib2.urlopen(url)
                dest.write(response.read())
    except KeyboardInterrupt:
        ### handle keyboard interrupt ###
        return E_OK
    except Exception as e:
        if logger.isEnabledFor(logging.DEBUG):
            raise(e)
        sys.stderr.write(os.path.basename(sys.argv[0]) + " : " + repr(e) + "\n")
        sys.stderr.write("    for help use --help")
        return E_ERR
    return E_OK


if __name__ == "__main__":
    sys.exit(run())
