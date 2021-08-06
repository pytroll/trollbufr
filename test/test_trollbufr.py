"""Unit tests for trollbufr package."""
# trollbufr unittest
#
# Copyright (C) 2017-2021 trollbufr developers
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
#
import os
import unittest

test_dir = os.path.dirname(os.path.abspath(__file__))


def test_bufr_read(monkeypatch):
    """Test reading data and data quality on Metop-A MHS BUFR file."""
    monkeypatch.setenv("BUFR_TABLES", os.path.join(test_dir, "bufrtables"))
    monkeypatch.setenv("BUFR_TABLES_TYPE", "bufrdc")
    from trollbufr import load_file
    from trollbufr.bufr import Bufr
    test_file = os.path.join(test_dir, "metop_mhs.bufr")
    bufr = Bufr(os.environ["BUFR_TABLES_TYPE"], os.environ["BUFR_TABLES"])
    # laod test file and iterate over BUFR
    for blob, size, header in load_file.next_bufr(test_file):
        # test header for first BUFR
        assert header == "IEMX01 EUMP 150722"
        assert size == 48598
        # decode BUFR message
        bufr.decode(blob)
        # iterate over subsets
        for report in bufr.next_subset():
            i = 0
            # iterate over all descriptor/data sets
            for k, m, (v, q) in report.next_data():
                i += 1
                if i >= 4:
                    # after first 3 descriptor/data sets just count
                    continue
                if i <= 3:
                    # type-marker for first 3 descriptor is not None
                    assert m is not None
                    continue
                # assert descriptor, data value, quality
                assert m is not None
                assert k == 8070
                assert v == 3
                assert q is None
                # look-up and assert name and unit
                kn, ku = bufr.get_tables().lookup_elem(k)
                assert kn.strip() == "TOVS/ATOVS PRODUCT QUALIFIER"
                assert ku.strip() == "CODE TABLE 8070"
            # assert there were 88 descriptors in the subset
            assert i == 88
            # leave for-loops, all tests are done
            break
        break


if __name__ == "__main__":
    unittest.run()
