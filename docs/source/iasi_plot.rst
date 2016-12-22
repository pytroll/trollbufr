WMO file formats
================

Wether you like it or not, the *Binary Universal Form for the Representation of 
meteorological data* (BUFR) file format (see e.g. the WMO_ satellite file format pages)
is widely used even in satellite meteorology.
The format is used mostly for satellite sounder data, like NOAA AMSU and MHS and Metop 
IASI, which traditionally have been the primary satellite data going into the *Numerical 
Weather Prediction* (NWP) models.

Here we will demonstrate how trollbufr (trollbufr_) can be used to read satellite 
data in BUFR format.

The Grib file format is another WMO file format. Traditionally this has been the 
file format used for the output of NWP models, but it is occasionally also used for storing 
satellite products. For reading Grib files in python we refer to the excellent 
pygrib_ package. 

Use python-bufr
---------------

The trollbufr does not depend on the ECMWF or ony other third-party BUFR 
library, but their (or any other provider's) tables, including EUMETSAT's local 
extension tables.
Although this example uses numpy, trollbufr does not require it.

Please see the package documentation at trollbufr_ for installation and setup.

You will just need to tell your environment where to find the BUFR tables and 
make sure your PYTHONPATH includes the place where you have the trollbufr installed:

     export BUFR_TABLES=/path/bufrtables/

In the BUFR_TABLES directory you will have files (and symlinks) like shown here:

.. code-block:: ini

     lrwxrwxrwx 1 a000680 users     24 26 jan 14.19 D0000000000254013001.TXT -> D0000000000098013001.TXT*
     lrwxrwxrwx 1 a000680 users     24 26 jan 14.19 C0000000000254013001.TXT -> C0000000000098013001.TXT*
     lrwxrwxrwx 1 a000680 users     24 26 jan 14.09 B0000000000254013001.TXT -> B0000000000098013001.TXT*
     lrwxrwxrwx 1 a000680 users     24 26 jan 14.00 D0000000000254010001.TXT -> D0000000000098013001.TXT*
     lrwxrwxrwx 1 a000680 users     24 26 jan 14.00 D0000000000099010001.TXT -> D0000000000098013001.TXT*
     ...

Example on EUMETCast IASI level 2 product
-----------------------------------------

    >>> TESTFILE = "./sample_data/iasi_20120206_190254_metopa_27506_eps_o_clp.l2_bufr"
    >>> import bufr
    >>> import numpy as np
    >>> bfr = bufr.BUFRFile(TESTFILE)

Import the required modules:

	>>> from trollbufr.bufr import Bufr
	>>> from trollbufr import load_file
	>>> import numpy as np
	>>> import sys
	>>> testfile = "./sample_data/IEDX61_EUMC_020505.bin"

Initialise the Bufr-object:
	
	>>> bfr = Bufr("eccodes", "tables")

Decode the BUFR's meta-data and print it to STDOUT:

	>>> for blob, size, header in load_file.next_bufr(testfile):
	>>>     bfr.decode(blob)
	>>>     print "\n", testfile, header, "\n", bfr.get_meta_str()

Let's have a look at the descriptor-list of the BUFR:

	>>>     print "\n".join( bufr.get_descr_full() )

.. code-block:: ini
   
	001007 : 'SATELLITE IDENTIFIER' (code) [CODE TABLE]
	001031 : 'IDENTIFICATION OF ORIGINATING/GENERATING CENTRE (SEE NOTE 10)' (code) [CODE TABLE]
	025060 : 'SOFTWARE IDENTIFICATION (SEE NOTE 2)' (long) [Numeric]
	002019 : 'SATELLITE INSTRUMENTS' (code) [CODE TABLE]
	002020 : 'SATELLITE CLASSIFICATION' (code) [CODE TABLE]
	004001 : 'YEAR' (long) [a]
	004002 : 'MONTH' (long) [mon]
	...
	005001 : 'LATITUDE (HIGH ACCURACY)' (double) [deg]
	006001 : 'LONGITUDE (HIGH ACCURACY)' (double) [deg]
	...
	008003 : 'VERTICAL SIGNIFICANCE (SATELLITE OBSERVATIONS)' (code) [CODE TABLE]
	112003 : LOOP, 12 desc., 3 times
	202129 : OPERATOR 2: 129
	201131 : OPERATOR 1: 131
	007004 : 'PRESSURE' (long) [Pa]
	201000 : OPERATOR 1: 0
	202000 : OPERATOR 2: 0
	012101 : 'TEMPERATURE/DRY-BULB TEMPERATURE' (double) [K]
	202130 : OPERATOR 2: 130
	201135 : OPERATOR 1: 135
	020081 : 'CLOUD AMOUNT IN SEGMENT' (long) [%]
	201000 : OPERATOR 1: 0
	202000 : OPERATOR 2: 0
	020056 : 'CLOUD PHASE' (code) [CODE TABLE]

In the BUFR file data are layed out sequentially, the pressure fields have the 
descriptors 007004. They are associated with the latitude 005001 and longitude 
006001.

Now lets just check what fields and their values are in the file, 
the first subset is enough to get an impression:

	>>>     for subset in bfr.next_subset():
	>>>         for k, m, (v, q) in subset.next_data():
	>>>             print k, m, v
	>>>         break

.. code-block:: ini
   
	Edition                         : 4
	Master-table                    : 0
	Centre                          : EUMETSAT OPERATION CENTRE
	Sub-Centre                      : NO SUB-CENTRE
	Update sequence number          : 0
	Type of data                    : observed
	Data category                   : Vertical soundings (satellite)
	International data sub-category : 255
	Local data sub-category         : 226
	Version number of master table  : 19
	Version number of local table   : 1
	Most typical time               : 2016-12-02 05:02:00
	Optional section present        : no
	Compression                     : yes
	Number of data subsets          : 2040
	None SUB None
	1007 None 4
	1031 None 254
	25060 None 602
	2019 None 221
	2020 None 61
	4001 None 2016
	4002 None 12
	4003 None 2
	4004 None 5
	4005 None 2
	4006 None 59
	5040 None 52516
	5041 None 175
	5001 None 71.1056
	6001 None 177.8049
	...
	None RPL 1 None
	7004 None 83637
	12101 None 247.0
	20081 None 86.13
	20056 None 2
	None RPL 2 None
	7004 None None
	12101 None None
	20081 None None
	20056 None None
	None RPL 3 None
	7004 None None
	12101 None None
	20081 None None
	20056 None None
	None RPL END None
	2040 2040 2040

We want to look at the Cloud Top Pressure, but we see that there are actually
three PRESSURE fields (repetitions RPL 1-3) in the file. 
The descritors are printed as numbers, leaving any leading "0". So we are 
looking for descriptors 5001, 6001, and 7004.

Since for the last two 7004 there's "None" in the third column, it seems the 
only field that contains data is the first one. Let us extract all the data 
and the geolocation:

    >>> bfr = bufr.BUFRFile(TESTFILE)
    >>> lon = []
    >>> lat = []
    >>> pres = []
    >>>     for subset in bfr.next_subset():
    >>>         gotit = 0
    >>>         for k, m, (v, q) in subset.next_data():
    >>>             if gotit:
    >>>                 continue
    >>>             if k == 5001:
    >>>                 lat.append((0, 0, v))
    >>>             if k == 6001:
    >>>                 lon.append((0, 0, v))
    >>>             if k == 7004:
    >>>                 pres.append((0, 0, v))
    >>>                 gotit = 1
    >>> lons = np.concatenate(lon) 
    >>> lats = np.concatenate(lat)
    >>> pres = np.concatenate(pres) / 100.0 # hPa
    >>> pres = np.ma.masked_greater(pres, 1.0e+6)


Now we have an IASI granule with the level 2 CTP parameter.
It is geolocated, so we could project it to a user area and map projection.
We use pyresample_ for that of course, and a predefined area from a local configuration 
file (see further below):

    >>> import pyresample as pr
    >>> from pyresample import kd_tree, geometry
    >>> from pyresample import utils
    >>> swath_def = geometry.SwathDefinition(lons=lons, lats=lats)
    >>> area_def = utils.parse_area_file('./region_config.cfg', 'scan2')[0]
    >>> result = kd_tree.resample_nearest(swath_def, pres,
                                  area_def, 
                                  radius_of_influence=12000, 
                                  epsilon=100,
                                  fill_value=None)
    >>> pr.plot.save_quicklook('/tmp/iasi_ctp.png', 
                        area_def, result, label='IASI - Cloud Top Pressure',
                        coast_res = 'h')


.. image:: images/iasi_ctp.png

The local area configuration is actually, in this case, taken from another project, 
namely the nwcsaf_. The NWCSAf PPS software use the same configuration style as
implemented in pyresample. In this particular case the area *scan2* is defined as 
shown below:

.. code-block:: ini
    
    REGION: scan2 {
        NAME:           Scandinavia - 2km area
        PCS_ID:         ps60n
        PCS_DEF:        proj=stere,ellps=bessel,lat_0=90,lon_0=14,lat_ts=60
        XSIZE:          1024
        YSIZE:          1024
        AREA_EXTENT:    (-1268854.1266382949, -4150234.8425892727, 779145.8733617051, -2102234.8425892727)
    };

.. _WMO:  http://www.wmo.int/pages/prog/sat/formatsandstandards_en.php
.. _pygrib: http://code.google.com/p/pygrib/
.. _trollbufr: http://github.com/pytroll/trollbufr
.. _pyresample: http://github.com/pytroll/pyresample
.. _nwcsaf: http://nwcsaf.smhi.se/
