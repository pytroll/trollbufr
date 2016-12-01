.. api_

API
=====

Usage
---------
Follow these steps:

1. Instantiate class Bufr
2. Load BUFR data in string
3. Decode BUFR data
4. Load tables
5. Get iterator over subsets
6. Get iterator over data elements and iterate

Repeat 5+6 for each subset.

Repeat 2-6 for new BUFR, re-using already loaded tables.

Classes and modules
--------------------

.. automodule:: trollbufr.bufr
   :members:

.. automodule:: trollbufr.reader
   :members:
