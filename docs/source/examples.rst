.. examples_

Examples
========

reader.py
---------
This gives good examples how to handle the class :class:`~trollbufr.bufr.Bufr`.

trollbufr_read
--------------

- Reading data elements::
	
	trollbufr_read -t tables -r data/mw/TestBulletin_051

  Decoding all BUFR in the file TestBulletin_051, for each reading the data
  elements and writing the descriptor, short name, value, unit to STDOUT.

- Simple list of descriptors::
	
	trollbufr_read -t tables -T libdwd -sdb 1 data/mw/TestBulletin_051

  Using the table-format `libdwd` and decoding only the first BUFR in the file, 
  writing the un-expanded list of descriptors (without names, etc.) to STDOUT.

trollbufr_update
----------------
Download archive file(s) from Internet resources to update the BUFR table files.

- URL(s) on command-line::

	trollbufr_update -t tables -U https://opendata.dwd.de/weather/lib/bufr/bufrtables_libdwd.tar.bz2

- Set of URLs in a file::

	trollbufr_update -t tables -F bufr_table_archives.txt

Bufr
----
Simple example for handling class :class:`Bufr`::

    bufr = Bufr(args.tables_type, args.tables_path)
    for fn in glob("*.bufr"):
        for blob, size, header in load_file.next_bufr(fn):
            print "HEADER\t%s" % header
            bufr.decode(blob, tables=False)
            tabl = bufr.load_tables()
            print "META:\n%s" % bufr.get_meta_str()
            for report in bufr.next_subset():
                print "SUBSET\t#%d/%d" % report.subs_num
                for k, m, (v, q) in report.next_data():
                    print k, v

Read all files named \*.bufr, parse each file for BUFR bulletins; then decode 
them, writing each descriptor and the associated data value to STDOUT.
					