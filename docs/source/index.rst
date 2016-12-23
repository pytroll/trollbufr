.. trollBUFR documentation master file, created by
   sphinx-quickstart on Tue Nov 29 12:56:03 2016.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to trollBUFR's documentation!
=====================================

Contents
--------
.. toctree::
   :maxdepth: 2

   tables
   api
   examples
   
trollBUFR
---------
The Python package ``trollbufr`` provides an API and some command-line scripts
to read/decode BUFR messages.

Where comes the *troll* from? -- Well, this reader lives in the context of 
PyTroll_ (an Open-Source-Software collaboration of several national 
meteorological services and universities.)

About BUFR
----------
BUFR stands for "Binary Universal Format for data Representation". 
It is a binary message format, developed as a "table-driven code form" (TDCF)
by members of World Meteorological Organisation (WMO_).

It's main use is the meteorological data exchange and storage. It is used
in other fields of geo-science as well, e.g. oceanographics, and 
satellite-derived products.

Find further information and detailed description at 
http://www.wmo.int/pages/prog/www/WMOCodes.html

To-Do
-----
There are still thing to do:

- Script for table download/update
- Implement the remaining obscure operators

So, get involved at PyTroll_ or GitHub_!

Indices and tables
==================

- :ref:`genindex`
- :ref:`modindex`
- :ref:`search`

.. _PyTroll: http://www.pytroll.org
.. _GitHub: https://github.com/alexmaul/trollbufr
.. _WMO: http://www.wmo.int