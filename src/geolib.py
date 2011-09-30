#!/usr/bin/env python
# -*- coding: utf-8  -*-
'''
This library provides geographic-related functions.
'''

import math

__author__ = "Mac Ryan"
__copyright__ = "Copyright ©2011, Mac Ryan"
#__credits__ = ["Name Lastname", "Name Lastname"]
__license__ = "GPL v3"
#__version__ = "<dev>"
#__date__ = "<unknown>"
__maintainer__ = "Mac Ryan"
__email__ = "quasipedia@gmail.com"
__status__ = "Development"
__all__ = ['orthodromic_dist']

EARTH_RADIUS = 6371   # in Km

def orthodromic_dist(point_a, point_b):
    '''
    Calculate the orthodromic distance between two GPS readings.

    point_a and point_b can be either of the two:
    - tuples in the form (latitude, longitude).
    - dictionaries having X, Y keys (as for example records of the class
      RawLog
    The result is in metres.

    ATTENTION: since latitude is given before longitude, if we are using the
    X and Y representation, then we must pass in (Y, X) and *not* (X, Y)

    Computed with the Haversine formula
    (http://en.wikipedia.org/wiki/Haversine_formula)
    '''
    if type(point_a) == dict:
        point_a = (point_a['X'], point_a['Y'])
    if type(point_b) == dict:
        point_b = (point_b['X'], point_b['Y'])
    func = lambda x : math.radians(float(x))
    a_lat, a_lon = map(func, point_a)
    b_lat, b_lon = map(func, point_b)
    d_lat = b_lat - a_lat
    d_lon = b_lon - a_lon
    a = math.sin(d_lat/2.0)**2 + math.cos(a_lat) * math.cos(b_lat) \
        * math.sin(d_lon/2.0)**2
    c = 2 * math.asin(math.sqrt(a))
    return EARTH_RADIUS * c * 1000
