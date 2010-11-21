#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
Created on 1 Nov 2010

@author: mac

@file: This module doubles as a standalone application, and it is intended
to import raw log data files (text lines) into the log database.
'''

import os.path
import sys
import getopt
import re
import datetime
import argparse
import textwrap
import zipfile
import kmlbase
import kmldom
import kmlengine
from storm.locals import *
from commons import *


class LogDataBase(object):

    '''
    Provide the interface for manipulating the Log DataBase.
    '''

    def __init__(self, fname=LOG_DB_FNAME, overwrite=False):
        self.db_file_name = fname
        new_db = not os.path.isfile(fname)
        if not new_db and overwrite:
            os.unlink(fname)
            new_db = True
        database = create_database('sqlite:' + fname)
        self.store = Store(database)
        if new_db:
            self._generate_schema()

    def _generate_schema(self):
        '''
        Generate the schema of the DB introspectively.
        '''
        # SIGNALS (contains all the log entries)
        query_signal_table = 'CREATE TABLE signals \
                (id INTEGER PRIMARY KEY, time VARCHAR UNIQUE'
        entries = LOG_SIGNALS.values()
        # Sort columns alphabetically (just for readability of DB schema
        entries.sort(cmp=lambda x, y: cmp(x[0], y[0]))
        for entry in entries:
            query_signal_table += ' '.join((', ', entry[0], entry[2]))
        query_signal_table += ')'
        # STINTS (contain information about each logged stint)
        query_stint_table = 'CREATE TABLE stints (id INTEGER PRIMARY KEY, \
                description VARCHAR, start_signal INTEGER, \
                stop_signal INTEGER)'
        self.store.execute(query_signal_table, noresult=True)
        self.store.execute(query_stint_table, noresult=True)
        self.store.commit()

    def _delta_t_signals(self, signal_a, signal_b):
        '''
        Returns the delta time in seconds between two signals.
        '''
        return (signal_b.ardu_millis - signal_a.ardu_millis) / 1000.0

    def _check_if_moved(self, from_signal, to_signal):
        '''
        Return True if the boat has moved beyond threshold between the two
        points.
        '''
        space = gps_distance_between(from_signal, to_signal)
        time = self._delta_t_signals(from_signal, to_signal)
        return True if space / time > STINT_SPEED_THRESHOLD else False

    def add_signals(self, signals):
        '''
        Add signals into the DB.

        Input signals are a list of strings.
        '''
        for signal in signals:
            tmp = Signal()
            signal = signal.replace('!', '')
            bits = signal.split()
            tmp.time = datetime.datetime.fromtimestamp(float(bits[0]))
            for bit in bits[1:]:
                k, v = bit.split(':')
                v = int(v) if v.find('.') == -1 else float(v)
                setattr(tmp, LOG_SIGNALS[k][0], v)
            self.store.add(tmp)
        self.store.commit()

    def import_log(self, infile):
        '''
        Parse a text log and add all it's signals to the DB.
        '''
        self.add_signals(LogTextFile(infile).clean_from_debug_symbols())

    def find_stints(self, from_id=None, to_id=None, db_save=False):
        '''
        Find stints in a record set.

        from_id and to_id identify the search pool. They default to the signal
        id following the last signal already belonging to a stint and to the
        last signal in the database respectively.

        If db_save is set to True, stints are saved with canned names in
        the database.

        Return a list of stints in the form [(start_id, end_id), ...]

        A stint is defined as all the GPS reading in an interval of time during
        which the boat kept on moving at at least STINT_SPEED_THRESHOLD m/s
        within units of time of the duration of STINT_TIME_SAMPLE s.
        '''

        # If not passed, the range is all signals after last recorded stint.
        if from_id == None:
            from_id = self.store.find(Stint).max(Stint.stop_signal)
            from_id = from_id if from_id else 0  # If no stints found...
        if to_id == None:
            to_id = self.store.find(Signal).max(Signal.id)
            if to_id == None:  # DB is empty
                return []
        result = self.store.find(Signal, Signal.id >= from_id,
                                 Signal.id <= to_id).order_by(Signal.id)
        # Start looking for stints
        stints = []
        start_signal = None
        last_positive = None
        previous = result[0]
        for current in result[1:]:
            if self._check_if_moved(previous, current):
                if not start_signal:
                    start_signal = previous
                last_positive = current
            else:
                if start_signal:
                    if self._delta_t_signals(last_positive, current) > \
                       STINT_MAX_STILL_TIME:
                        if self._delta_t_signals(start_signal, last_positive) \
                           > STINT_MINIMUM_LENGTH:
                            stints.append((start_signal.id, last_positive.id))
                        start_signal = None
                        last_positive = None
            previous = current
        if db_save == True:
            print "hei!"
            for stint in stints:
                self.store.add(Stint(stint[0], stint[1]))
            self.store.commit()
        return stints

    def get_kml(self, param):
        '''
        Return the kml file of a given range.

        It is possible to pass either a range (signal_first_id, signal_last_id)
        or a stint ID.
        '''
        if not isinstance(param, tuple):
            stint = self.store.get(Stint, param)
            start = stint.start_signal
            stop = stint.stop_signal
        else:
            stint = None
            start, stop = param
        signals = self.store.find(Signal,
                                  And(Signal.id >= start, Signal.id <= stop))
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
        for signal in signals:
            coordinates.add_latlng(signal.latitude, signal.longitude)
            # Individual signals
            tmp = factory.CreatePlacemark()
            tmp.set_name("#" + str(signal.id))
            msg = ''
            msg += 'North: ' + str(signal.north)
            msg += '\nRudder: ' + str(signal.rudder_position)
            msg += '\nSail: ' + str(signal.sail_position)
            if prev:
                m = gps_distance_between(prev, signal)
                ms = signal.ardu_millis - prev.ardu_millis
                speed = m / ms
                msg += '\nSpeed (cm/s): ' + str(int(speed * 100000))
                msg += '\nSpeed (km/h): ' + str('%.2f' % (speed * 3600))
            tmp.set_description(msg)
            point = factory.CreatePoint()
            pcoord = factory.CreateCoordinates()
            pcoord.add_latlng(signal.latitude, signal.longitude)
            point.set_coordinates(pcoord)
            tmp.set_geometry(point)
            document.add_feature(tmp)
            prev = signal
        document.add_feature(placemark)
        linestring = factory.CreateLineString()
        linestring.set_tessellate(True)
        linestring.set_coordinates(coordinates)
        placemark.set_geometry(linestring)
        # Create the KML file
        kml = factory.CreateKml()
        kml.set_feature(document)
        return kmldom.SerializePretty(kml)

    def get_db_stats(self):
        '''
        Return an dictionary containing statistics about the database.

        Keys:
        size                size in bytes
        signal_number       number of log signals
        stint_number        number of stints
        orphans             number of log_signals not belonging to a stint
        stints              a list of "get_stint_stats" dictionaries
        '''
        result = {}
        result['size'] = os.path.getsize(self.db_file_name)
        result['signal_number'] = None
        result['stint_number'] = None
        result['orphans'] = None
        result['stints'] = None


class StormIntrospective(type):

    '''
    Metaclass to make generation of storm classes introspective.
    '''

    def __init__(self, name, bases, attrs):
        more = attrs.get('moreattrs')
        if more:
            for attr, val in more.iteritems():
                setattr(self, attr, val)


class Signal(object):

    '''
    Storm descriptor for table 'signals'.

    It uses a metaclass to make the setting of the properties introspective.
    '''

    __metaclass__ = StormIntrospective
    __storm_table__ = "signals"
    id = Int(primary=True)
    time = DateTime()
    moreattrs = {}
    for entry in LOG_SIGNALS.values():
        if entry[2] == 'INTEGER':
            storm_class = Int()
        if entry[2] == 'REAL':
            storm_class = Float()
        moreattrs[entry[0]] = storm_class
    del storm_class  # Otherwise it gets interpreted as a field in the table!


class Stint(object):

    '''
    Storm descriptor for table 'stints'.
    '''

    __storm_table__ = "stints"
    id = Int(primary=True)
    description = Unicode()
    start_signal = Int()
    stop_signal = Int()

    def __init__(self, start, stop, description=u"AutoStint"):
        self.start_signal = start
        self.stop_signal = stop
        self.description = description


class LogTextFile(object):

    '''
    Provide the interface for manipulating the Log text-only file.
    '''

    def __init__(self, input_file=LOG_RAW_FNAME):
        self.input = open(input_file, 'r')

    def clean_from_debug_symbols(self):
        '''
        Remove all non-logging signals from the raw_log.

        It uses a regex to do this: all log messages are identified as those
        lines beginning with a timestamp, followed by a space, followed by an
        exclamation mark.
        '''
        cregex = re.compile('^\d+\.\d+ !')
        output = []
        for line in self.input.readlines():
            if cregex.match(line):
                output.append(line)
        return output

    def manipulate(self, output_file=None, clean_only=False, stints=False,
                   verbose=False, overwrite=False, **kwargs):
        '''
        Manipulate the input file.

        This method allows to manipulate the input data by for example cleaning
        it from debug symbols or importing it into the Logging database.
        '''
        # if output_file == None:
        # output_file = LOG_CLEAN_FNAME if clean_only else LOG_DB_FNAME
        file_mode = 'w' if overwrite else 'a'
        cleaned_log = self.clean_from_debug_symbols()
        if verbose:
            print("Clean log has %d lines" % len(cleaned_log))
        if clean_only:
            try:
                output = open(output_file, file_mode)
            except:
                print "Impossible to write to the output file!"
            for line in cleaned_log:
                output.write(line)
            output.close()
            if verbose:
                print "Output file successfully saved. Size: %d bytes" % \
                        os.path.getsize(output_file)
            return
        db = LogDataBase(output_file, overwrite)
        db.import_signals(cleaned_log)
        if verbose:
            print "DB updated. Current size: %d bytes" % \
                    os.path.getsize(output_file)
        if stints:
            stints = db.find_stints(db_save=True)
            if verbose:
                print "%d stints have been identified in the new recordset." \
                        % len(stints)


class CommandLine(object):

    '''
    Provide help methods to use the module as a command-line utility.
    '''

    def __init__(self):
        '''
        Parse the command and forward request to specialised method.

        Returns a Namespace object in which "func" is the callback for the
        subcommand, and all the rest are parameters.
        '''
        # Create main parser
        parser = argparse.ArgumentParser(
            description='''Utility for processing logs generated by the
                           MagellanMachine project.''',
            epilog='''Try "./log.py <command> -h" for specific help on
                      individual commands.''')
        parser.add_argument('infile',
            help='Input file', nargs='?', default=argparse.SUPPRESS)
        parser.add_argument('outfile',
            help='Output file', nargs='?', default=argparse.SUPPRESS)
        subparsers = parser.add_subparsers(title='subcommands')
        # CLEAN
        parser_clean = subparsers.add_parser('clean',
            help='Remove debug messages from a text log file',
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog=textwrap.dedent('''\
            Defaults:
              infile   :  %s
              outfile  :  %s''' % (LOG_RAW_FNAME, LOG_CLEAN_FNAME)))
        parser_clean.set_defaults(func=self.clean_raw)
        # IMPORT
        parser_import = subparsers.add_parser('import',
            help='Import a text log file into the DB',
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog=textwrap.dedent('''\
            Defaults:
              infile   :  %s
              outfile  :  %s''' % (LOG_RAW_FNAME, LOG_DB_FNAME)))
        parser_import.add_argument('-a', '--auto',
            help='''Automatically identify stints (equivalent to running
                    "stints --auto" after the import)''',
            action='store_const', const=True)
        parser_import.add_argument('--overwrite',
            help='Overwrite DB instead of appending data to it',
            action='store_const', const=True)
        parser_import.set_defaults(func=self.import_raw)
        # STINTS
        parser_stints = subparsers.add_parser('stints',
            help='''Identify stints in the database. Note that the outfile is
                    always forced to be the same as the input file''',
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog=textwrap.dedent('''\
            Defaults:
              infile   :  %s
              outfile  :  ALWAYS forced to be the same as infile''' % \
                                   LOG_DB_FNAME))
        parser_stints.add_argument('-f', '--from',
            help='''Process only signals from and including ID. If omitted, the
                    command will search for stings starting from signal
                    following the last signal known to already belong to a
                    stint''',
            type=int, dest='from_id', metavar='ID')
        parser_stints.add_argument('-t', '--to',
            help='Process only signals up to and including ID',
            type=int, dest='to_id', metavar='ID')
        parser_stints.add_argument('-s', '--save',
            help='Save found stints in the database',
            dest='db_save', action='store_const', const=True)
        parser_stints.set_defaults(func=self.find_stints)
        # EXPORT
        parser_export = subparsers.add_parser('export',
            help='Export a stint as KML or KMZ file',
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog=textwrap.dedent('''\
            Defaults:
              infile   :  %s
              outfile  :  %s<ID>.kml [.kmz if -z option used]''' % \
                                   (LOG_DB_FNAME, LOG_PATH_FNAME)))
        parser_export.add_argument('-z', '--zip',
            help='Produce a KMZ file instead of a KML',
            action='store_const', const=True)
        parser_export.add_argument('stints',
            help='The stints IDs for which to create the file',
            type=int, metavar='ID', nargs='+')
        parser_export.set_defaults(func=self.export_to_keyhole_files)
        # STATS
        parser_stats = subparsers.add_parser('stats',
            help='Provide stats on database content',
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog=textwrap.dedent('''\
            Defaults:
              infile   :  %s
              outfile  :  <stdout>''' % LOG_DB_FNAME))
        parser_stats.set_defaults(func=self.not_implemented)
        # Do parsing of commandline
        args = parser.parse_args()
        func = args.func
        del args.func
        func(**args.__dict__)

    def clean_raw(self, infile=LOG_RAW_FNAME, outfile=LOG_CLEAN_FNAME):
        raw = LogTextFile(infile)
        lines = raw.clean_from_debug_symbols()
        file = open(outfile, 'w')
        file.writelines(lines)
        file.close()
        return lines

    def import_raw(self, infile=LOG_RAW_FNAME, outfile=LOG_DB_FNAME,
                         overwrite=False, auto=False):
        db = LogDataBase(outfile, overwrite)
        db.import_log(infile)
        if auto:
            self.find_stints(infile=outfile, db_save=True)

    def find_stints(self, infile=LOG_DB_FNAME, from_id=None,
                    to_id=None, db_save=False):
        db = LogDataBase(infile)
        stints = db.find_stints(from_id, to_id, db_save)
        print('%d stints have been found in the recordset' % len(stints))
        for stint in stints:
            print(stint[0], stint[1])

    def export_to_keyhole_files(self, stints, zip=False,
                                infile=LOG_DB_FNAME, outfile=LOG_PATH_FNAME):
        db = LogDataBase(infile)
        for stint in stints:
            kml_name = outfile + str(stint) + '.kml'
            kmz_name = outfile + str(stint) + '.kmz'
            xml = db.get_kml(stint)
            if zip:
                file = zipfile.ZipFile(kmz_name, 'w')
                file.writestr(kml_name, xml)
                file.close()
            else:
                file = open(kml_name, 'w')
                file.write(xml)
                file.close()

    def not_implemented(self, **kwargs):
        print("This functionality hasn't been implemented yet.")
        print kwargs


if __name__ == '__main__':
    CommandLine()
