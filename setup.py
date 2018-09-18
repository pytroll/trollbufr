#!/usr/bin/env python
# -*- coding: utf-8 -*-
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

"""
"""
# workaround python bug: http://bugs.python.org/issue15881#msg170215
import multiprocessing

from setuptools import setup, find_packages
import imp
import sys

version = imp.load_source("trollbufr.version", "trollbufr/version.py")

requires = ["bitstring"]

setup(name="trollbufr",
      version=version.__version__,
      description="Reading meteorological data format BUFR in pure Python",
      author="Alexander Maul",
      author_email="alexander.maul@dwd.de",
      classifiers=["Development Status :: 4 - Beta",
                   "Intended Audience :: Science/Research",
                   "License :: OSI Approved :: GNU Lesser General Public License v3 " +
                   "or later (LGPLv3+)",
                   "Operating System :: OS Independent",
                   "Programming Language :: Python :: 3",
                   "Programming Language :: Python :: 3.4",
                   "Topic :: Scientific/Engineering"
                   ],
      test_suite="bufr.tests.suite",
      entry_points={
          "console_scripts": ["trollbufr3 = trollbufr.bufr_main:run",
                              "trollbufr3_update = trollbufr.update:run"]},
      packages=["trollbufr", "trollbufr.coder"],
      install_requires=requires,
      python_requires=">=3.4",
      zip_safe=False,
      )
