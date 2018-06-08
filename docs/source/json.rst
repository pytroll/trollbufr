.. json_

JSON Format for Input/Output
============================

.. contents::

Purpose
-------
The JSON object notation format was chosen because numerous reader are
available, and it's also human-readable.
The structure has its focus on values, rather any descriptive elements, as it
is the same with binary BUFR.

Decode BUFR to JSON Output
--------------------------
To decode a BUFR into a JSON object, either use the instance method
`Bufr.decode()` or the command-line parameter ``-j | --decode-json``.

Encode JSON Input to BUFR
-------------------------
To encode a file with a JSON object into binary BUFR, either use the instance
method `Bufr.encode()` or the command-line parameter ``-e | --encode``.

JSON Structure
--------------
The content of an input and output file as formatted following the JSON
structure consist of one list ``[...]`` as top-level element.

Each entry in this list represents one BUFR message.

One BUFR message is build as a dictionary ``{...}`` with following keys:

- `"index"` : integer value, equal to the list index of this BUFR in the top-level
  list.

- `"file"` : optional, set if the command-line scripts are used for decoding and
  encoding:

    - Original file name, if a file was decoded.
    - File name used for encoding.

- `"heading"` : optional,

    - Set if the decoded file contained a WMO bulletin.
    - Used as WMO abbreviated heading line for a WMO bulletin on encoding.


- `"bufr"` : the value representation of the BUFR.

Example::

    [{
        "index": 0,
        "bufr": [ ... ],
        "heading": null,
        "file": "207003.bufr"
    }]

The value representation of one BUFR is one list ``[...]``, its elements are
the BUFR sections 0 to 4, where each is a list of values.

Length identifyer
~~~~~~~~~~~~~~~~~
In contrast to the binary BUFR, there are NO length values denoting either the
length of a section, or the ammount of repetition. On encoding they will be
calculated, thus making the handling of delayed replication easier.

Booleans, None, Strings, and Numbers
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
With JSON, boolean values are encoded as ``true`` or ``false``, which is the
case for some flag-values in sections 1 and 3.

In the data section 4, for any `missing value` the keyword ``none`` is set in
the JSON structure.

Strings, or character sequences, are stored as sequences of ITA-5 (which is
equivalent to US-ASCII) characters, surrounded with double-quotes ``"``.
When encoding a JSON object as BUFR, the underlying functions take care of
padding/truncating the strings to match the width as defined by the descriptor.

Numbers are ... numbers. Either integer or decimal-point values.

Section 0 -- Indicator section
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Always has exactly two elements:

- the keyword ``"BUFR"``.
- the BUFR edition number.

::

    ["BUFR", 3],

Section 1 -- Identification section
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
The identification elements, or meta-data, of this BUFR.

The elements meaning follows the same order as encoded in BUFR according to
the BUFR edition.

Although the representative time is encoded in BUFR Ed.3 without a value for
the seconds, they are always set in the JSON structure -- in which case they
are set to zero.
On encoding a JSON structure into BUFR Ed.3, the value for seconds will be
ignored.

::

    [0, 0, 98, 0, false, 21, 202, 15, 0, 2012, 11, 2, 0, 0, 0],

Section 2 -- Optional section (local data)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
This section is optional in encoding a BUFR, but the corresponding list entry
is required.

Empty section::

    [],

If the local data section 2 should not be present in the BUFR when
encoding or decoding, the list representing the values of this section shall be
left empty.

Section with values::

    ["03", "59", "7d", "ca", "7d", "20", "00", "53", "10", "94"],

If data for local application use either was encoded in the BUFR or should be
used when encoding a BUFR, the numerical ASCII values of all bytes shall be
listed, each wrapped with double-quotes to set string values.

Section 3 -- Data description section
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Values listed in the following order:

- Number of data subsets.
- Data category flag.
- Data compression flag.
- Collection of descriptors which define the form and content of individual
  data elements.

::

    [2, true, true, ["310060"]],

Section 4 -- Data section
~~~~~~~~~~~~~~~~~~~~~~~~~
Binary data.


Section 5 -- End section
~~~~~~~~~~~~~~~~~~~~~~~~
Always has exactly one element: the keyword ``"7777"``.

::

    ["7777"]

Full Example
~~~~~~~~~~~~

.. include:: _static/207003.json
    :code: javascript

