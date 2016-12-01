Tables
======

Download TDCF table archive:

* zip-files (``bufrtables_*.zip``) in this project.
* eg. from `ECMWF eccodes <https://software.ecmwf.int/wiki/display/ECC/ecCodes+Home>`_.
* DWD's public `FTP server for GDS <http://www.dwd.de/EN/ourservices/gds/gds.html>`_.
* Or other sources.

If files operator.table and/or datacat.table are not present in the table directory, 
there are standard ones in this project's root. These files are not required for 
decoding, but optional for readable output.

Either set environment variable ``$BUFR_TABLES`` to the base directory, where the table
archives were extracted into, or provide this path to the Bufr constructor, 
resp. at command-line.
