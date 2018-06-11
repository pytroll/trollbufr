.. usage_

Usage
=====

The class Bufr provides methods for decoding and encoding BUFR with different
strategies:

- Decode BUFR meta-data from BUFR section 0, 1, and 3.
- Decode data section 4 only.
- Load tables corresponding to BUFR section 1.
- Do all three steps in one go.
- Encode a JSON formatted file as BUFR and write this to a file.

Decoding the data section can be done descriptor by descriptor via a generator,
or decode it in one step, creating a JSON-like data structure.
The second will have better performance with BUFR using the internal compression.


Usually follow these first steps to decode a BUFR:

1. Instantiate class Bufr
2. Load BUFR data in string
3. Decode BUFR meta-data
4. Load tables

To retrieve the descriptor/value pairs from a generator:

5. Get iterator over subsets
6. Get iterator over data elements and iterate

Repeat 5+6 for each subset.

To decode a BUFR and retrieve all values as a JSON-like structure:

5. Decode all values from all subsets, and get a dict object.

Repeat 2-6 for new BUFR, re-using already loaded tables.



