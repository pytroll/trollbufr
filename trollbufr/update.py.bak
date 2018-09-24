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
import tarfile
import zipfile
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
    parser.add_argument("-s", "--strip",
                        help="strip N top-level dirs on un-tar",
                        type=int,
                        metavar="N",
                        )
    parser.add_argument("--download",
                        action="store_true",
                        help="only download table archives"
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


def download_all(args, url_list):
    """Command line options."""
    arc_list = []
    for url in url_list:
        try:
            arc_name = url.split("/")[-1]
            arc_dest = os.path.join(args.tables_path, arc_name)
            if not os.path.exists(args.tables_path):
                logger.warning("Path does not exist: %s", args.tables_path)
                return E_ARG
            with open(arc_dest, "w") as dest:
                logger.info("Download %s", url)
                response = urllib2.urlopen(url)
                dest.write(response.read())
        except StandardError as e:
            logger.warning("%s : %s", url, e)
        else:
            arc_list.append(arc_dest)
    return arc_list


def un_tar(args, arc_dest):
    """Extract (compressed) TAR file."""
    logger.info("Extract %s", arc_dest)
    with tarfile.open(arc_dest, "r") as tar_h:
        for member in tar_h:
            name_parts = member.name.split(os.path.sep)[args.strip:]
            if not len(name_parts):
                continue
            new_name = os.path.sep.join(name_parts)
            if member.isdir():
                try:
                    logger.debug("mkdir: %s", new_name)
                    os.makedirs(os.path.join(args.tables_path, new_name))
                except:
                    pass
            elif member.isfile():
                with open(
                        os.path.join(args.tables_path, new_name),
                        "w") as fh:
                    logger.debug("write: %s", new_name)
                    fh.write(tar_h.extractfile(member).read())


def un_zip(args, arc_dest):
    """Extract ZIP file."""
    logger.info("Extract %s", arc_dest)
    with zipfile.ZipFile(arc_dest, "r") as zip_h:
        for member in zip_h.infolist():
            name_parts = member.filename.split(os.path.sep)[args.strip:]
            if not len(name_parts):
                continue
            new_name = os.path.sep.join(name_parts)
            if member.filename.endswith("/"):
                try:
                    logger.debug("mkdir: %s", new_name)
                    os.makedirs(os.path.join(args.tables_path, new_name))
                except:
                    pass
            else:
                with open(
                        os.path.join(args.tables_path, new_name),
                        "w") as fh:
                    logger.debug("write: %s", new_name)
                    fh.write(zip_h.open(member).read())


def run(argv=None):
    if argv is None:
        argv = sys.argv
    else:
        sys.argv.extend(argv)
    args = arg_parser()
    if args.url:
        url_list = args.url
    elif args.url_file:
        url_list = []
        with open(args.url_file, "r") as fh_url:
            for line in fh_url:
                url_list.append(line.strip())
    else:
        logger.error("URL or URL-file missing!\n")
        return E_ERR
    try:
        print args
        logger.debug("Sources: %s", url_list)
        logger.debug("Destination: %s", args.tables_path)
        arc_list = download_all(args, url_list)
        if not args.download:
            for arc_dest in arc_list:
                try:
                    if tarfile.is_tarfile(arc_dest):
                        un_tar(args, arc_dest)
                    elif zipfile.is_zipfile(arc_dest):
                        un_zip(args, arc_dest)
                    else:
                        logger.warning("Unkown archive format: %s", arc_dest)
                except StandardError as e:
                    logger.warning("Extract %s : %s", arc_dest, e)
                else:
                    os.remove(arc_dest)
    except KeyboardInterrupt:
        ### handle keyboard interrupt ###
        return E_OK
    except StandardError as e:
        logger.error(e)
        return E_ERR
    return E_OK


if __name__ == "__main__":
    sys.exit(run())
