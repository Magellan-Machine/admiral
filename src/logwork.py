#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
Created on 1 Nov 2010

@author: mac

@file: This module doubles as a standalone application, and it is intended
to import raw log data files (text lines) into the log database.
'''

import os.path, sys, getopt
import re
import datetime
from storm.locals import *
from commons import *
import kmlbase, kmldom, kmlengine


class LogDataBase(object):
    
    '''
    Provide the interface for manipulating the Log DataBase.
    '''

    def __init__(self, fname=LOG_DB_FNAME, overwrite=False):
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
        query_signal_table = 'CREATE TABLE signals (id INTEGER PRIMARY KEY, time VARCHAR UNIQUE'
        entries = LOG_SIGNALS.values()
        # Sort columns alphabetically (just for readability of DB schema 
        entries.sort(cmp = lambda x, y: cmp(x[0], y[0]))
        for entry in entries:
            query_signal_table += ' '.join((', ', entry[0], entry[2]))
        query_signal_table += ')'
        # STINTS (contain information about each logged stint)
        query_stint_table = 'CREATE TABLE stints (id INTEGER PRIMARY KEY, description VARCHAR, start_signal INTEGER, stop_signal INTEGER)'
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
        Return True if the boat has moved beyond threshold between the two points.
        '''
        space = gps_distance_between(from_signal, to_signal)
        time  = self._delta_t_signals(from_signal, to_signal)
        return True if space/time > STINT_SPEED_THRESHOLD else False
        
    def import_signals(self, signals):
        '''
        Import a series of signals into the DB.
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
        
    def find_stints(self, range=None, db_save=False):
        '''
        Find stints in a record set.
        
        range is a tuple (start, finish) with the id of the signals identifying
        the search pool. If set to None, stints are found starting from the id
        following the last id already belonging to a stint.
        If db_save is set to True, stints are saved with canned names in
        the database.
        Return a list of stints in the form [(start_id, end_id), ...]

        A stint is defined as all the GPS reading in an interval of time during
        which the boat kept on moving at at least STINT_SPEED_THRESHOLD m/s
        within units of time of the duration of STINT_TIME_SAMPLE s.        
        '''
        
        # If not passed, the range is all signals after last recorded stint.
        if range == None:
            last = self.store.find(Signal).max(Signal.id)
            if last == None: # DB is empty
                return 0 
            first = self.store.find(Stint).max(Stint.stop_signal)
            first = first if first else 0 # If no stints have been found...
        else:
            first, last = range
        result = self.store.find(Signal, Signal.id >= first, Signal.id <= last).order_by(Signal.id)
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
                    if self._delta_t_signals(last_positive, current) > STINT_MAX_STILL_TIME:
                        if self._delta_t_signals(start_signal, last_positive) > STINT_MINIMUM_LENGTH:
                            stints.append((start_signal.id, last_positive.id))
                        start_signal = None
                        last_positive = None
            previous = current
        if db_save == True:
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
        signals = self.store.find(Signal, And(Signal.id >= start, Signal.id <= stop))
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
                speed = m/ms
                msg += '\nSpeed (cm/s): ' + str(int(speed*100000))
                msg += '\nSpeed (km/h): ' + str('%.2f' % (speed*3600))
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
        print kmldom.SerializePretty(kml)


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
    del storm_class # Otherwise it gets interpreted as a field in the table!


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

    def __init__(self, input_file=LOG_RAW_FNAME, **kwargs):
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
        if output_file == None:
            output_file = LOG_CLEAN_FNAME if clean_only else LOG_DB_FNAME
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
                print "Output file successfully saved. Size: %d bytes" % os.path.getsize(output_file)
            return
        db = LogDataBase(output_file, overwrite)
        db.import_signals(cleaned_log)
        if verbose:
            print "DB updated. Current size: %d bytes" % os.path.getsize(output_file)
        if stints:
            stints = db.find_stints(db_save=True)
            if verbose:
                print "%d stints have been identified in the new recordset." % len(stints)

def _usage():
    print main.__doc__

def main(argv):
    '''
    The Magellan Machine project ©2010.
    Utility for processing raw boat logs.
    
    Usage: log.py [options] [<input-file>] [<output-file>]
    
    Options:
    -c --clean-only  : clean the log file from debugging messages
                       (do not write to database)    -h --help        : display this help message
    -o --overwrite   : overwrite target file instead of appending data to it
    -s --stints      : automatically identify stints (DB)
    -v --verbose     : display extra information while running
    
    Defaults:
    <input-file>     : ../data/raw_msg.log
    <output-file>    : ../data/db.log | ../data/clean_msg.log (with -c option)
    '''
    # Parse options
    try:                                
        opts, args = getopt.getopt(argv, "chosv", ["clean-only", "help", "overwrite", "stints", "verbose"])
    except getopt.GetoptError:
        print "Unable to parse options."
        _usage()
        sys.exit(2)
    # Check that apart options there is only the input file name
    if len(args) > 2:
        print "Too much stuff on the command line:", ' '.join(args[1:])
        _usage()
        sys.exit(2)
    # Check for existence of input file if given
    if len(args) > 0:
        try:
            f = file(args[0], 'r')
            f.close()
        except:
            print "Unable to open input file named \"%s\"" % args[0] 
            _usage()
            sys.exit(2)
    # Set command parameters
    flags = {}
    if len(args) > 0:
        flags['input_file'] = args[0]
    if len(args) > 1:
        flags['output_file'] = args[1]
    for opt, arg in opts:
        if opt in ("-c", "--clean-only"):
            flags['clean_only'] = True
        if opt in ("-s", "--stints"):
            flags['stints'] = True
        if opt in ("-v", "--verbose"):
            flags['verbose'] = True
        if opt in ("-o", "--overwrite"):
            flags['overwrite'] = True
        if opt in ("-h", "--help"):
            _usage()
            sys.exit()
    # Execute import
    input = LogTextFile(**flags)
    input.manipulate(**flags)
    
if __name__ == '__main__':
    db = LogDataBase(fname='/home/mac/Desktop/log/trial.sqlite')
    db.get_kml(1)
#    main(sys.argv[1:])