#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Log manager for the Magellan Machine.

This module can be used by admiral to parse logs and import them into the main
MagellanMachine database. It also doubles as a standalone application, allowing
to create keywhole files to be viewed with google Earth and others.
'''

#import os.path
#import re
#import datetime
#import argparse
#import textwrap
#import zipfile
#import kmlbase
#import kmldom
#import kmlengine

import os.path
from calendar import timegm
from time import strptime
from collections import deque

import matplotlib.pyplot as plt

import geolib

__author__ = "Mac Ryan"
__copyright__ = "Copyright ©2011, Mac Ryan"
#__credits__ = ["Name Lastname", "Name Lastname"]
__license__ = "GPL v3"
#__version__ = "<dev>"
#__date__ = "<unknown>"
__maintainer__ = "Mac Ryan"
__email__ = "quasipedia@gmail.com"
__status__ = "Development"


def NoMovementError(StandardError):
    '''
    Exception class raised when calculations on a log bring to the conclusion
    the boat did not move.
    '''

#    def _check_if_moved(self, from_signal, to_signal):
#        '''
#        Return True if the boat has moved beyond threshold between the two
#        points.
#        '''
#        space = gps_distance_between(from_signal, to_signal)
#        time = self._delta_t_signals(from_signal, to_signal)
#        return True if space / time > STINT_SPEED_THRESHOLD else False
#
#    def find_stints(self, from_id=None, to_id=None, db_save=False):
#        '''
#        Find stints in a record set.
#
#        from_id and to_id identify the search pool. They default to the signal
#        id following the last signal already belonging to a stint and to the
#        last signal in the database respectively.
#
#        If db_save is set to True, stints are saved with canned names in
#        the database.
#
#        Return a list of stints in the form [(start_id, end_id), ...]
#
#        A stint is defined as all the GPS reading in an interval of time during
#        which the boat kept on moving at at least STINT_SPEED_THRESHOLD m/s
#        within units of time of the duration of STINT_TIME_SAMPLE s.
#        '''
#
#        # If not passed, the range is all signals after last recorded stint.
#        if from_id == None:
#            from_id = self.store.find(Stint).max(Stint.stop_signal)
#            from_id = from_id if from_id else 0  # If no stints found...
#        if to_id == None:
#            to_id = self.store.find(Signal).max(Signal.id)
#            if to_id == None:  # DB is empty
#                return []
#        result = self.store.find(Signal, Signal.id >= from_id,
#                                 Signal.id <= to_id).order_by(Signal.id)
#        # Start looking for stints
#        stints = []
#        start_signal = None
#        last_positive = None
#        previous = result[0]
#        for current in result[1:]:
#            if self._check_if_moved(previous, current):
#                if not start_signal:
#                    start_signal = previous
#                last_positive = current
#            else:
#                if start_signal:
#                    if self._delta_t_signals(last_positive, current) > \
#                       STINT_MAX_STILL_TIME:
#                        if self._delta_t_signals(start_signal, last_positive) \
#                           > STINT_MINIMUM_LENGTH:
#                            stints.append((start_signal.id, last_positive.id))
#                        start_signal = None
#                        last_positive = None
#            previous = current
#        if db_save == True:
#            print "hei!"
#            for stint in stints:
#                self.store.add(Stint(stint[0], stint[1]))
#            self.store.commit()
#        return stints
#
#    def get_kml(self, param):
#        '''
#        Return the kml file of a given range.
#
#        It is possible to pass either a range (signal_first_id, signal_last_id)
#        or a stint ID.
#        '''
#        if not isinstance(param, tuple):
#            stint = self.store.get(Stint, param)
#            start = stint.start_signal
#            stop = stint.stop_signal
#        else:
#            stint = None
#            start, stop = param
#        signals = self.store.find(Signal,
#                                  And(Signal.id >= start, Signal.id <= stop))
#        factory = kmldom.KmlFactory_GetFactory()
#        # Create the embedding document
#        document = factory.CreateDocument()
#        document.set_name("MagellanMachine sailing")
#        # Create the style
#        line_style = factory.CreateLineStyle()
#        line_style.set_color(kmlbase.Color32('7f00ffff'))
#        line_style.set_width(4)
#        style = factory.CreateStyle()
#        style.set_id("mmstyle")
#        style.set_linestyle(line_style)
#        document.add_styleselector(style)
#        # Create the placemarks
#        placemark = factory.CreatePlacemark()
#        placemark.set_name("Name Foo Bar!")
#        placemark.set_styleurl("#mmstyle")
#        coordinates = factory.CreateCoordinates()
#        prev = None
#        for signal in signals:
#            coordinates.add_latlng(signal.latitude, signal.longitude)
#            # Individual signals
#            tmp = factory.CreatePlacemark()
#            tmp.set_name("#" + str(signal.id))
#            msg = ''
#            msg += 'North: ' + str(signal.north)
#            msg += '\nRudder: ' + str(signal.rudder_position)
#            msg += '\nSail: ' + str(signal.sail_position)
#            if prev:
#                m = gps_distance_between(prev, signal)
#                ms = signal.ardu_millis - prev.ardu_millis
#                speed = m / ms
#                msg += '\nSpeed (cm/s): ' + str(int(speed * 100000))
#                msg += '\nSpeed (km/h): ' + str('%.2f' % (speed * 3600))
#            tmp.set_description(msg)
#            point = factory.CreatePoint()
#            pcoord = factory.CreateCoordinates()
#            pcoord.add_latlng(signal.latitude, signal.longitude)
#            point.set_coordinates(pcoord)
#            tmp.set_geometry(point)
#            document.add_feature(tmp)
#            prev = signal
#        document.add_feature(placemark)
#        linestring = factory.CreateLineString()
#        linestring.set_tessellate(True)
#        linestring.set_coordinates(coordinates)
#        placemark.set_geometry(linestring)
#        # Create the KML file
#        kml = factory.CreateKml()
#        kml.set_feature(document)
#        return kmldom.SerializePretty(kml)
#
#    def get_db_stats(self):
#        '''
#        Return an dictionary containing statistics about the database.
#
#        Keys:
#        size                size in bytes
#        signal_number       number of log signals
#        stint_number        number of stints
#        orphans             number of log_signals not belonging to a stint
#        stints              a list of "get_stint_stats" dictionaries
#        '''
#        result = {}
#        result['size'] = os.path.getsize(self.db_file_name)
#        result['signal_number'] = None
#        result['stint_number'] = None
#        result['orphans'] = None
#        result['stints'] = None


class RawLog(list):

    '''
    Provide the interface for manipulating the Log text-only file.

    RawLog are subclasses of lists. Each list element is a dictionary in the
    form {field_name: field_value}.
    '''

    def __init__(self, fname):
        super(list,self).__init__(self)
        basename = os.path.basename(fname)
        self.log_start_time = timegm(strptime(basename[:-4], '%Y-%m-%d@%Hh%M'))
        self.__load_raw_file(fname)

    def __load_raw_file(self, fname):
        '''
        Load the raw data into self (each line on the log becomes an element
        of the list represented by the RawLog object).
        '''
        start = self.log_start_time
        for line in open(fname):
            fields = line.strip().split(',')
            record = dict([(f[0], f[1:]) for f in fields[1:]])
            record['timestamp'] = start + int(fields[0]) / 1000.0
            self.append(record)

    def plot(self):
        '''
        Draw a basic analysis of the log.
        Useful to define the stints.
        '''
        print "Intial length: %i" % len(self)
        self.strip()
        print "Stripped length: %i" % len(self)
        self.filter_gps_locked()
        print "Length after GPS faulty signals: %i" % len(self)
        self.filter_minimum_step_length(5)
        print "Length after GPS minimum step_length: %i" % len(self)

        plt.figure()
        # SPEED
        plt.subplot(2, 2, 1)
        plt.ylabel('speed [m/s]')
        func = lambda x, y : geolib.orthodromic_dist(x, y) \
                             / (y['timestamp'] - x['timestamp'])
        plt.plot(map(func, self[:-1], self[1:]), color='red')
        plt.grid(True)
        # DISTANCE FROM ORIGIN
        plt.subplot(2, 2, 3)
        plt.ylabel('distance from origin [m]')
        func = lambda x : geolib.orthodromic_dist(self[0], x)
        plt.plot(map(func, self))
        plt.grid(True)
        plt.xlabel('record serial number')
        # PATTERN SKETCH
        plt.subplot(1, 2, 2)
        plt.xlabel('approximate representation')
        x_es = [el['X'] for el in self]
        y_es = [el['Y'] for el in self]
        plt.plot(x_es, y_es, color='green')
        frame1 = plt.gca()
        frame1.axes.get_xaxis().set_ticks([])
        frame1.axes.get_yaxis().set_ticks([])
        plt.show()

    def strip(self, mov_threshold=5, rewind_time=5):
        '''
        Filter out initial and final non meaningful records.

        Typically these records indicate that the system was already / still
        ON, but the boat was handled manually (probably on the deck, for pre or
        post navigation operations.

        The logic adopted to identify the non-relevant records is two folded:
        * An initial series of identical coordinates denote that the
          GPS was not yet getting a live fixes.
        * All initial or final movements that do not move the boat beyond
          the ``threshold`` are considered like "on dock" movements.
        The logic is in two steps as when the GPS acquire the fix, it might
        "jump" several metres from the origin, but we don't want this to
        trigger the "threshold" condition.

        Return data about the performed stripping in the form of a dictionary.
        '''
        ops = {}
        # ELIMINATE initial entries with no GPS fix
        i = self._get_movement_start_index(self, 0, 0)
        self[:] = self[i:]
        ops['no_fix_start'] = i
        # ELIMINATE final entries with no GPS fix
        i = self._get_movement_start_index(self[::-1], 0, 0)
        self[:] = self[:len(self)-i]
        ops['no_fix_end'] = i
        # ELIMINATE INITIAL LINGERING
        i = self._get_movement_start_index(self, mov_threshold, rewind_time)
        self[:] = self[i:]
        ops['lingering_start'] = i
        # ELIMINATE INITIAL LINGERING
        i = self._get_movement_start_index(self[::-1], mov_threshold,
                                                       rewind_time)
        self[:] = self[:len(self)-i]
        ops['lingering_end'] = i
        return ops

    def filter_gps_locked(self):
        '''
        Eliminates all records in which the GPS has subsequent equal fixes.
        (This is normally a sign that the fix has been lost).
        '''
        data = []
        fix = lambda r: (r['X'], r['Y'])
        test = lambda i: len(set([fix(self[c]) for c in range(i-1, i+2)])) == 3
        self.insert(0, dict(X=None, Y=None))
        self.append(dict(X=None, Y=None))
        for i in range(1, len(self)-1):
            if test(i):
                data.append(self[i])
        self[:] = data

    def filter_minimum_step_length(self, step_lenght):
        '''
        Selectively remove log entries in order to obtain a log in which each
        entry has a distance from the previous one of at least ``step_lenght``
        metres [the last entry of self is always kept, regardless].
        '''
        data = [self[0]]
        for i in range(1, len(self)):
            if geolib.orthodromic_dist(data[-1], self[i]) > step_lenght:
                data.append(self[i])
        data.append(self[-1])
        self[:] = data

    def stats(self):
        '''
        Return an dictionary containing statistics about the database.

        Keys:
        signal_number       number of log signals
        stint_number        number of stints
        orphans             number of log_signals not belonging to a stint
        stints              a list of "get_stint_stats" dictionaries
        '''
        pass

    def _get_movement_start_index(self, data, threshold, rewind_time):
        '''
        Return the index of the first element in ``data`` that is part of a
        boat movement.

        - ``threshold``: distance in metres from first point in series
        - ``rewind_time``: time in second in which the movement is assumed to
          have started before the threshold limit was triggered.
        '''
        # Find the index of the first point over the threshold
        for i in range(len(data)):
            if geolib.orthodromic_dist(data[0], data[i]) > threshold:
                triggering_time = data[i]['timestamp']
                for i in range(i, 0, -1):
                    time_diff = abs(data[i]['timestamp'] - triggering_time)
                    if time_diff > rewind_time:
                        return i+1
                return i
        return None


#class CommandLine(object):
#
#    '''
#    Provide help methods to use the module as a command-line utility.
#    '''
#
#    def __init__(self):
#        '''
#        Parse the command and forward request to specialised methods.
#
#        Returns a Namespace object in which "func" is the callback for the
#        subcommand, and all the rest are parameters.
#        '''
#        # Create main parser
#        parser = argparse.ArgumentParser(
#            description='''Utility for processing logs generated by the
#                           MagellanMachine project.''',
#            epilog='''Try "./logman.py <command> -h" for specific help on
#                      individual commands.''')
#        parser.add_argument('infile',
#            help='Input file', nargs='?', default=argparse.SUPPRESS)
#        parser.add_argument('outfile',
#            help='Output file', nargs='?', default=argparse.SUPPRESS)
#        subparsers = parser.add_subparsers(title='subcommands')
#        # STINTS
#        parser_stints = subparsers.add_parser('stints',
#            help='''Identify stints in the database. Note that the outfile is
#                    always forced to be the same as the input file''',
#            formatter_class=argparse.RawDescriptionHelpFormatter,
#            epilog=textwrap.dedent('''\
#            Defaults:
#              infile   :  %s
#              outfile  :  ALWAYS forced to be the same as infile''' % \
#                                   LOG_DB_FNAME))
#        parser_stints.add_argument('-f', '--from',
#            help='''Process only signals from and including ID. If omitted, the
#                    command will search for stings starting from signal
#                    following the last signal known to already belong to a
#                    stint''',
#            type=int, dest='from_id', metavar='ID')
#        parser_stints.add_argument('-t', '--to',
#            help='Process only signals up to and including ID',
#            type=int, dest='to_id', metavar='ID')
#        parser_stints.add_argument('-s', '--save',
#            help='Save found stints in the database',
#            dest='db_save', action='store_const', const=True)
#        parser_stints.set_defaults(func=self.find_stints)
#        # EXPORT
#        parser_export = subparsers.add_parser('export',
#            help='Export a stint as KML or KMZ file',
#            formatter_class=argparse.RawDescriptionHelpFormatter,
#            epilog=textwrap.dedent('''\
#            Defaults:
#              infile   :  %s
#              outfile  :  %s<ID>.kml [.kmz if -z option used]''' % \
#                                   (LOG_DB_FNAME, LOG_PATH_FNAME)))
#        parser_export.add_argument('-z', '--zip',
#            help='Produce a KMZ file instead of a KML',
#            action='store_const', const=True)
#        parser_export.add_argument('stints',
#            help='The stints IDs for which to create the file',
#            type=int, metavar='ID', nargs='+')
#        parser_export.set_defaults(func=self.export_to_keyhole_files)
#        # STATS
#        parser_stats = subparsers.add_parser('stats',
#            help='Provide stats on database content',
#            formatter_class=argparse.RawDescriptionHelpFormatter,
#            epilog=textwrap.dedent('''\
#            Defaults:
#              infile   :  %s
#              outfile  :  <stdout>''' % LOG_DB_FNAME))
#        parser_stats.set_defaults(func=self.not_implemented)
#        # Do parsing of commandline
#        args = parser.parse_args()
#        func = args.func
#        del args.func
#        func(**args.__dict__)
#
#    def clean_raw(self, infile=LOG_RAW_FNAME, outfile=LOG_CLEAN_FNAME):
#        raw = LogTextFile(infile)
#        lines = raw.clean_from_debug_symbols()
#        file = open(outfile, 'w')
#        file.writelines(lines)
#        file.close()
#        return lines
#
#    def import_raw(self, infile=LOG_RAW_FNAME, outfile=LOG_DB_FNAME,
#                         overwrite=False, auto=False):
#        db = LogDataBase(outfile, overwrite)
#        db.import_log(infile)
#        if auto:
#            self.find_stints(infile=outfile, db_save=True)
#
#    def find_stints(self, infile=LOG_DB_FNAME, from_id=None,
#                    to_id=None, db_save=False):
#        db = LogDataBase(infile)
#        stints = db.find_stints(from_id, to_id, db_save)
#        print('%d stints have been found in the recordset' % len(stints))
#        for stint in stints:
#            print(stint[0], stint[1])
#
#    def export_to_keyhole_files(self, stints, zip=False,
#                                infile=LOG_DB_FNAME, outfile=LOG_PATH_FNAME):
#        db = LogDataBase(infile)
#        for stint in stints:
#            kml_name = outfile + str(stint) + '.kml'
#            kmz_name = outfile + str(stint) + '.kmz'
#            xml = db.get_kml(stint)
#            if zip:
#                file = zipfile.ZipFile(kmz_name, 'w')
#                file.writestr(kml_name, xml)
#                file.close()
#            else:
#                file = open(kml_name, 'w')
#                file.write(xml)
#                file.close()


if __name__ == '__main__':
    pass
#    CommandLine()
