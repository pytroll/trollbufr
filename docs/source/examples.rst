.. examples_

Examples
========

Using the trollbufr-API, the class :class:`~trollbufr.bufr.Bufr` presents the
main entry point.

trollbufr.bufr_main.py
~~~~~~~~~~~~~~~~~~~~~~
This gives good examples how to handle the class :class:`~trollbufr.bufr.Bufr`.

trollbufr.bufr.Bufr
~~~~~~~~~~~~~~~~~~~
Simple example for handling class :class:`Bufr`::

    bufr = Bufr(args.tables_type, args.tables_path)
    for fn in glob("*.bufr"):
        for blob, size, header in load_file.next_bufr(fn):
            print "HEADER\t%s" % header
            bufr.decode_meta(blob, tables=False)
            tabl = bufr.load_tables()
            print "META:\n%s" % bufr.get_meta_str()
            for report in bufr.next_subset():
                print "SUBSET\t#%d/%d" % report.subs_num
                for k, m, (v, q) in report.next_data():
                    print k, v

Read all files named \*.bufr, parse each file for BUFR bulletins; then decode
them, writing each descriptor and the associated data value to STDOUT.

It can be done even shorter::

    bufr = Bufr(args.tables_type, args.tables_path)
    for fn_in in glob("*.bufr"):
        for blob, _, header in load_file.next_bufr(fn_in):
            json_bufr = bufr.decode(blob,
                                    load_tables=True,
                                    as_array=args.array)
            print json_bufr

Here each BUFR is decoded, including loading tables as required, in one go and
the resulting values are printed as a list/dict structure.

