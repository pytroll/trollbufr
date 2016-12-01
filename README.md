# trollBUFR
A pure pythonic reader for BUFR, the meteorological 
"Binary Universal Format for data Representation"

_(C) 2016 Alexander Maul_

## Tables
Download TDCF table archive:
* zip-files (bufrtables_*) in this project.
* eg. from [ECMWF eccodes](https://software.ecmwf.int/wiki/display/ECC/ecCodes+Home).
* DWD's public [FTP server for GDS](http://www.dwd.de/EN/ourservices/gds/gds.html).
* Or other sources.
If files operator.table and/or datacat.table are not present in the table directory, 
there are standard ones in this project's root. These files are not required for 
decoding, but optional for readable output.

Either set environment variable `$BUFR_TABLES` to the base directory, where the table
archives were extracted into, or provide this path to the Bufr constructor, 
resp. at command-line.

## Command-line program "trollbufr_read"
Command-line interface, reads BUFR (with abbreviated heading line,
if present) from file(s) and writes human-readable to stdout.

## To-Do
* Script for table download/update
* Implement the remaining obscure operators
