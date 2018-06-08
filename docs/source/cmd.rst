Command-line scripts
====================

Two command-line scripts will be created by `python setup.py install`.

Both print the available options with description for each option to STDOUT::

    trollbufr -h
    trollbufr --help

::

    trollbufr_update -h
    trollbufr_update --help

Executing them without any command-line option, they will just print the list
of options to STDOUT.

trollbufr
---------
This is a command-line script to call `bufr_main.py`.

- Reading data elements::

    trollbufr -t tables -d data/mw/TestBulletin_051

  Decoding all BUFR in the file TestBulletin_051, for each reading the data
  elements and writing the descriptor, short name, value, unit to STDOUT.
  The table format defaults to "eccodes".

  ::

    trollbufr -t tables -o Test.txt -d data/mw/TestBulletin_051

  Does the same as the first example, but writes to the file Test.txt.

- Simple list of descriptors::

    trollbufr -t tables -T libdwd -smb 1 data/mw/TestBulletin_051

  Using the table-format `libdwd` and decoding only the first BUFR in the file,
  writing the un-expanded list of descriptors (without names, etc.) to STDOUT.

- Encoding data from a JSON-formatted file as BUFR::

    trollbufr -t tables -e -o Test.bin data/TestBulletin_1.json

  Encodes the JSON-formatted content of the file TestBulletin_1.json and
  writes the resulting BUFR to the file Test.bin instead of STDOUT.


trollbufr_update
----------------
A command-line script to download archive file(s) from Internet resources in
order to update the BUFR table files.

- URL(s) on command-line, strip first two elements from path on extract::

    trollbufr_update -t tables -s 2 -U https://opendata.dwd.de/weather/lib/bufr/bufrtables_libdwd.tar.bz2

- Set of URLs in a file -- only download, no extract::

    trollbufr_update -t tables --download -F bufr_table_archives.txt

