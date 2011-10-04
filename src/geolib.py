#!/usr/bin/env python
# -*- coding: utf-8  -*-
'''
This library provides geographic-related functions.
'''

import math

import kmldom, kmlbase

__author__ = "Mac Ryan"
__copyright__ = "Copyright ©2011, Mac Ryan"
#__credits__ = ["Name Lastname", "Name Lastname"]
__license__ = "GPL v3"
#__version__ = "<dev>"
#__date__ = "<unknown>"
__maintainer__ = "Mac Ryan"
__email__ = "quasipedia@gmail.com"
__status__ = "Development"

EARTH_RADIUS = 6371   # in kilometres
NAUTICAL_MILE = 1852  # in metres
KNOT = 1.943844       # in metres/second

class SameRecordError(StandardError):
    '''
    Exception class raised when some function that is supposed to operate on
    two distinct points is called on the same one.
    '''

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

def orthodromic_speed(point_a, point_b):
    '''
    Return the speed between the boat had between ``point_a`` and ``point_b``,
    which needs to be log records (dictionaries).
    '''
    if point_a == point_b:
        raise SameRecordError
    dist = orthodromic_dist(point_a, point_b)
    time = abs(point_b['timestamp'] - point_a['timestamp'])
    return dist/time

def get_kml(records):
    '''
    Return the kml (keyhole markup language, Google Earth) file for a given set
    of records.
    '''
    factory = kmldom.KmlFactory_GetFactory()
    # Create the embedding document
    document = factory.CreateDocument()
    document.set_name("MagellanMachine sailing")
    # Create the style
    line_style = factory.CreateLineStyle()
    line_style.set_color(kmlbase.Color32('7f00ffff'))
    line_style.set_width(4)
    style = factory.CreateStyle()
    style.set_id("mmstyle")
    style.set_linestyle(line_style)
    document.add_styleselector(style)
    # Create the placemarks
    placemark = factory.CreatePlacemark()
    placemark.set_name("Name Foo Bar!")
    placemark.set_styleurl("#mmstyle")
    coordinates = factory.CreateCoordinates()
    prev = None
    for counter, record in enumerate(records):
        coordinates.add_latlng(record['Y'], record['X'])
        # Individual records
        tmp = factory.CreatePlacemark()
        tmp.set_name("#" + str(counter))
        est_speed = 0
        if prev:
            m = orthodromic_dist(prev, record)
            ms = record['timestamp'] - prev['timestamp']
            est_speed = m / ms
        msg_lines = []
        msg_lines.append('HDOP: ' + str(record['D']))
        msg_lines.append('GPS heading: ' + str(record['H']))
        msg_lines.append('GPS speed (cm/s): ' + str(int(record['F'] * 100)))
        msg_lines.append('GPS speed (km/h): ' + str(int(record['F'] * 3.6)))
        msg_lines.append('Estimated speed (cm/s): ' +
                         str(int(est_speed * 100)))
        msg_lines.append('Estimated speed(km/h): ' +
                         str('%.2f' % (est_speed * 3.6)))
        msg_lines.append('Sail PWM: ' + str(record['S']))
        msg_lines.append('Rudder PWM: ' + str(record['R']))
        tmp.set_description('\n'.join(msg_lines))
        point = factory.CreatePoint()
        pcoord = factory.CreateCoordinates()
        pcoord.add_latlng(record['Y'], record['X'])
        point.set_coordinates(pcoord)
        tmp.set_geometry(point)
        document.add_feature(tmp)
        prev = record
    document.add_feature(placemark)
    linestring = factory.CreateLineString()
    linestring.set_tessellate(True)
    linestring.set_coordinates(coordinates)
    placemark.set_geometry(linestring)
    # Create the KML file
    kml = factory.CreateKml()
    kml.set_feature(document)
    return kmldom.SerializePretty(kml)

def convert_from_si(dimension, quantity, unit_system):
    '''
    Convert **certain** dimensions from the SI unit system to others.
    '''
    if unit_system not in ('si', 'nautical', 'conventional'):
        raise RuntimeError('Unknown unit system')
    if dimension == 'distance':
        if unit_system == 'si':
            return quantity, 'm'
        elif unit_system == 'nautical':
            return float(quantity) / NAUTICAL_MILE, 'nmi'
        elif unit_system == 'conventional':
            return quantity / 1000.0, 'km'
    elif dimension == 'speed':
        if unit_system == 'si':
            return quantity, 'm/s'
        elif unit_system == 'nautical':
            return quantity * KNOT, 'kn'
        elif unit_system == 'conventional':
            return quantity * 3.6, 'kph'
    else:
        raise RuntimeError('Unknown dimension')
