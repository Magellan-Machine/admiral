#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Log manager for the Magellan Machine.

This module can be used by admiral to parse logs and import them into the main
MagellanMachine database. It also doubles as a standalone application, allowing
to create keywhole files to be viewed with google Earth and others.
'''

import itertools as itools
import re
import copy
import os.path
import time
import textwrap
import zipfile
from math import ceil
from datetime import timedelta
from calendar import timegm

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


class NoMovementError(StandardError):
    '''
    Exception class raised when calculations on a log bring to the conclusion
    the boat did not move.
    '''

class LogmanWrongFileName(StandardError):
    '''
    Exception class raised when the log filename does not contain a timestring
    in the format "HHHH-MM-DD@HHhMM".
    '''
    def __str__(self):
        return "A portion of the log file name must contain information on " \
               "the date and time of the sailing in the form: " \
               "'HHHH-MM-DD@HHhMM'."

class RawLog(list):

    '''
    Provide the interface for manipulating the Log text-only file.

    RawLog are subclasses of lists. Each list element is a dictionary in the
    form {field_name: field_value}.
    '''

    def __init__(self, fname):
        self.fname = fname
        super(list,self).__init__(self)
        basename = os.path.basename(fname)
        tmp = re.search(r'\d{4}(-\d{2}){2}@\d\dh\d\d', basename)
        try:
            t_bit = tmp.group()
        except AttributeError:
            raise LogmanWrongFileName()
        self.log_start_time = timegm(time.strptime(t_bit, '%Y-%m-%d@%Hh%M'))
        self.__load_raw_file(fname)

    def plot(self):
        '''
        Draw a basic analysis of the log.
        Useful to define the stints.
        '''
        plt.figure()
        # SPEED
        plt.subplot(3, 2, 1)
        plt.ylabel('speed [m/s]')
        func = lambda x, y : geolib.orthodromic_speed(x, y)
        plt.plot(map(func, self[:-1], self[1:]), color='red')
        plt.grid(True)
        # DISTANCE FROM ORIGIN
        plt.subplot(3, 2, 3)
        plt.ylabel('distance from origin [m]')
        func = lambda x : geolib.orthodromic_dist(self[0], x)
        plt.plot(map(func, self))
        plt.grid(True)
        plt.xlabel('record serial number')
        # HDOP
        plt.subplot(3, 2, 5)
        plt.ylabel('HDOP')
        plt.plot([record['D'] for record in self])
        plt.grid(True)
        plt.xlabel('record serial number')
        # PATTERN SKETCH
        plt.subplot(1, 2, 2)
        self._plot_sketch(self, 'Approximate representation')
        plt.show()

    def plot_stints(self, stints):
        '''
        Plot different stings in a side-by-side comparison.
        '''
        # Establish the grid matrix
        plt.figure()
        len_ = len(stints)
        col_n = ceil(len_**0.5)
        row_n = ceil(float(len_)/col_n)
        for i, stint in enumerate(stints):
            plt.subplot(col_n, row_n, i+1)
            start, stop = stint
            self._plot_sketch(self[start:stop], 'records %s to %s' % stint)
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

    def stints(self, radius, min_time):
        '''
        Split the log into distinct stints, where each stint is opened / closed
        by a period of at least ``min_time`` seconds in which the boat didn't
        move of more than ``min_range`` metres.
        '''
        dtime = lambda a, b: abs(a['timestamp'] - b['timestamp'])
        test_linger = lambda pool: self._get_min_circle_radius(pool) <= radius
        start = 0
        stop = 0
        lingering = [start]
        while True:
            print "%.2f" % (float((start + (stop-start) / 2)) / len(self)*100)
            if stop < len(self) and dtime(self[start], self[stop]) < min_time:
                stop += 1
                continue
            if start <= stop and not test_linger(self[start:stop]):
                start += 1
                continue
            # By now we must be in a lingering segment, so we can keep on
            # expanding it until the boat begins to move.
            print start, stop, len(self)
            while stop < len(self) and test_linger(self[start:stop]):
                stop += 1
            lingering.extend((start, stop))
            start = stop+1
            stop = start
            print start, stop, len(self)
            if start == stop == len(self) + 1:
                break
        return zip(*[lingering[i::2] for i in range(2)])

    def filter_by_HDOP(self, threshold):
        '''
        Eliminate all records whose DOP is over the threshold
        '''
        data = [r for r in self if r['D'] <= threshold]
        ops = {'removed_records': len(self) - len(data)}
        self[:] = data
        return ops

    def filter_minimum_step_length(self, step_lenght):
        '''
        Selectively remove log entries in order to obtain a log in which each
        entry has a distance from the previous one of at least ``step_lenght``
        metres.

        Return data about the performed filtering in the form of a dictionary.
        '''
        data = [self[0]]
        for i in range(1, len(self)):
            if geolib.orthodromic_dist(data[-1], self[i]) > step_lenght:
                data.append(self[i])
        ops = {'removed_records': len(self) - len(data)}
        self[:] = data
        return ops

    def stats(self):
        '''
        Return an dictionary containing statistics about the database.
        '''
        stats = {}
        # DATES and TIMES
        stats['time_log'] = self.log_start_time
        stats['time_first'] = self[0]['timestamp']
        stats['time_last'] = self[-1]['timestamp']
        stats['time_total'] = self[-1]['timestamp'] - self[0]['timestamp']
        # DISTANCES
        dist = lambda i, j : geolib.orthodromic_dist(self[i], self[j])
        individual_dists = [dist(i, i+1) for i in range(len(self)-1)]
        total = sum(individual_dists)
        furthest = max([dist(0, i) for i in range(len(self))])
        stats['dist_total'] = total
        stats['dist_furthest'] = furthest
        # SPEEDS
        stats['speed_avg'] = stats['dist_total'] / stats['time_total']
        chron = lambda i, j : self[j]['timestamp'] - self[i]['timestamp']
        individual_times = [chron(i, i+1) for i in range(len(self)-1)]
        stats['speed_max'] = max(map(lambda a, b: a/b,
                                     individual_dists, individual_times))
        # COUNTERS
        stats['counter_records'] = len(self)
        return stats

    def dump(self, fname):
        '''
        Dump the content of the log to a new file.
        '''
        lines = []
        for record in self:
            reverse_delta = record['timestamp'] - self.log_start_time
            bits = [str(int(round(reverse_delta * 1000, 0))).zfill(9)]
            for k in sorted(record):
                if k != 'timestamp':
                    bits.append(''.join((k, str(record[k]))))
            bits = ','.join(bits)
            lines.append(''.join([bits, '\n']))
        f = open(fname, 'w')
        f.writelines(lines)
        f.close()

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

    def _get_min_circle_radius(self, pool):
        '''
        Return the radius of the minimum encompassing circle.
        See: http://mathworld.wolfram.com/JungsTheorem.html
        '''
        pairs = itools.combinations(pool, 2)
        dist = geolib.orthodromic_dist
        return max([dist(*pair) for pair in pairs]) / 3**0.5

    def _plot_sketch(self, data, title):
        '''
        Draw an approximate representation of the log pattern on surface.
        '''
        plt.xlabel(title)
        x_es = [el['X'] for el in data]
        y_es = [el['Y'] for el in data]
        plt.plot(x_es, y_es, color='green', marker='o', markersize=3)
        frame1 = plt.gca()
        frame1.axes.get_xaxis().set_ticks([])
        frame1.axes.get_yaxis().set_ticks([])


    def __load_raw_file(self, fname):
        '''
        Load the raw data into self (each line on the log becomes an element
        of the list represented by the RawLog object).
        '''
        real = re.compile(r'^\d+\.\d+$')
        integer = re.compile(r'^\d+$')
        start = self.log_start_time
        for line in open(fname):
            fields = line.strip().split(',')
            record = dict([(f[0], f[1:]) for f in fields[1:]])
            # FIXME: Just a quick fix waiting to decide with the team how to
            #        handle log data...
            for k, v in record.items():
                if real.match(v):
                    record[k] = float(v)
                elif integer.match(v):
                    record[k] = int(v)
                # (the rest are strings)
            record['timestamp'] = start + int(fields[0]) / 1000.0
            self.append(record)


class CommandLine(object):

    '''
    Provide help methods to use the module as a command-line utility.
    '''

    def __init__(self):
        '''
        Parse the commands received on the command line.

        logman offers four different sub-commands, each of them with its own
        possible arguments. These are:

        - ``stats``: print statistics about the log
        - ``plot``: show math plotting of the log
        - ``filter``: filter the log
        - ``stints``: split the log in separate navigation stints
        - ``export``: export to a kml or kmz file
        '''
        # CREATE MAIN PARSER
        parser = argparse.ArgumentParser(
            description='''Utility for processing logs generated by the
                           MagellanMachine project.''',
            epilog='''Try "logman <command> -h" for specific help on
                      individual commands.''')
        common_parent_parser = argparse.ArgumentParser(add_help=False)
        common_parent_parser.add_argument('infile',
                            help='The log file to work with',
                            metavar='<INFILE>')
        common_parent_parser.add_argument('-f', '--first',
                            help='First record of the log to consider',
                            type=int,
                            metavar='N')
        common_parent_parser.add_argument('-l', '--last',
                            help='Last record of the log to consider',
                            type=int,
                            metavar='N')

        subparsers = parser.add_subparsers(title='subcommands')

        # STATS COMMAND
        parser_stats = subparsers.add_parser('stats',
            help='Print basic information about the log',
            parents=[common_parent_parser])
        help_msg = textwrap.dedent('''Allows to choose the unit system used
        for the statistics. Allowed choices are SI (metres, m/s), NAUTICAL
        (nautical miles, knots) and CONVENTIONAL (kilometres, kph).''')
        parser_stats.add_argument('-u', '--unit-system',
                                  choices=['SI', 'NAUTICAL', 'CONVENTIONAL'],
                                  default='SI',
                                  help=help_msg)
        parser_stats.set_defaults(func=self._stats)

        # PLOT COMMAND
        parser_plot = subparsers.add_parser('plot',
            help='''Plot various graphs useful to analyse the log''',
            parents=[common_parent_parser])
        parser_plot.set_defaults(func=self._plot)

        # FILTER COMMAND
        parser_filter = subparsers.add_parser('filter',
            help='''Allows to filter the log in various ways''',
            parents=[common_parent_parser])
        help_msg = textwrap.dedent('''The filtered log can be either plotted
        for analysys or saved to a ".filtered" file.''')
        parser_filter.add_argument('action',
                                   default='PLOT',
                                   choices=['PLOT', 'SAVE'],
                                   help=help_msg)
        help_msg = textwrap.dedent('''Try to automatically strip meaningless
        initial and/or final records of the log.
          MINMOV indicates after how many metres from the launch point the boat
        is considered "sailing" (this define the triggering record).
          REWIND: indicates the number of seconds of logging data that needs to
        be kept before the triggering record.
          MINMOV and REWIND are applied symmetrically at the end of the log
        (metres from final point, and seconds after that threshold has been
        crossed)''')
        parser_filter.add_argument('-s', '--strip',
                                   nargs=2,
                                   default=[],
                                   type=int,
                                   metavar=('MINMOV', 'REWIND'),
                                   help=help_msg)
        help_msg = textwrap.dedent('''Eliminates those records whose HDOP is
            above a given threshold.''')
        parser_filter.add_argument('-p', '--precision',
                                   type=float,
                                   metavar='MAX_HDOP',
                                   help=help_msg)
        help_msg = textwrap.dedent('''Selectively discards log records in order
            to obtain a log in which each record is separated by the previous
            and following ones by at least N metres.''')
        parser_filter.add_argument('-r', '--regular-steps',
                                   metavar='N',
                                   type=int,
                                   help=help_msg)
        parser_filter.set_defaults(func=self._filter)

        #STINTS COMMAND
        parser_stints = subparsers.add_parser('stints',
                      help='Split the log in separate navigation stints',
                      parents=[common_parent_parser])
        parser_stints.add_argument('radius',
                    type=int,
                    metavar='<RADIUS>',
                    help='Tolerance radius for considering the boat still [in'
                         'metres]')
        parser_stints.add_argument('mintime',
                    type=int,
                    metavar='<MINTIME>',
                    help='Minimum amount of time the boat must be in radius '
                         'to be considered still [in seconds].')
        parser_stints.set_defaults(func=self._stints)

        #EXPORT COMMAND
        parser_export = subparsers.add_parser('export',
                      help='Generate KML or KMZ files from a log',
                      parents=[common_parent_parser])
        parser_export.add_argument('-z', '--zip',
                           help='Produce a KMZ file instead of a KML',
                           action='store_true')
        parser_export.set_defaults(func=self._export)

        # DO THE PARSING
        kwargs = vars(parser.parse_args())
        kwargs['log'] = self._prepare_log(**kwargs)
        func = kwargs['func']
        for k in ('func', 'infile', 'first', 'last'):
            del kwargs[k]
        func(**kwargs)

    def _prepare_log(self, infile, first, last, **kwargs):  #@UnusedVariable
        '''
        Load the log and perform list comprehension on it.
        '''
        try:
            log = RawLog(infile)
        except LogmanWrongFileName as e:
            print "FATAL ERROR: %s" % e
            exit(1)
        if last:
            log[:] = log[:last]
        if first:  #must be after "last" as it will shift the index!
            log[:] = log[first-1:]
        return log

    def _stints(self, log, radius, mintime):
        '''
        Create stints
        '''
        stints = log.stints(radius, mintime)
        for start, stop in stints:
            fname = log.fname + '.[%s-%s]' % (start, stop)
            tmp = copy.deepcopy(log)
            tmp[:] = tmp[start:stop]
            tmp.dump(fname)
        log.plot_stints(stints)

    def _filter(self, log, strip, precision, regular_steps, action):
        '''
        Filter the log.

        The filtering order is:
        - by HDOP
        - stripping
        - regualar steps
        '''
        if precision:
            log.filter_by_HDOP(precision)
        if strip:
            log.strip(*strip)
        if regular_steps:
            log.filter_minimum_step_length(regular_steps)
        if action == 'PLOT':
            log.plot()
        elif action == 'SAVE':
            log.dump(log.fname + '.filtered')

    def _stats(self, log, unit_system):
        '''
        Print statistics.
        '''
        unit_system = unit_system.lower()
        UNIT_SYSTEMS_NAMES = dict(si='INTERNATIONAL SYSTEM OF UNITS',
                                  conventional='CONVENTIONAL UNITS',
                                  nautical='NAUTICAL UNITS')
        TEMPLATE = '  %-20s : %s'
        def conv(dimension, quantity):
            amount, units = geolib.convert_from_si(dimension, quantity,
                                                   unit_system)
            amount = round(amount, 3)
            return "%9s [%s]" % (amount, units)
        stats = log.stats()
        lines = []
        lines.append('')
        lines.append('### STATISTICS PROVIDED in %s #################' %
                     UNIT_SYSTEMS_NAMES[unit_system])
        lines.append('')
        lines.append('COUNTERS')
        lines.append(TEMPLATE % ('Number of records',
                                 stats['counter_records']))
        lines.append('')
        lines.append('TIMES')
        lines.append(TEMPLATE % ('Sailing date',
                                 time.strftime('%Y-%m-%d, %Hh%M',
                                          time.gmtime(stats['time_log']))))
        lines.append(TEMPLATE % ('Boat launched at',
                                 time.strftime('%Y-%m-%d, %Hh%M',
                                          time.gmtime(stats['time_first']))))
        lines.append(TEMPLATE % ('Boat retreived at',
                                 time.strftime('%Y-%m-%d, %Hh%M',
                                          time.gmtime(stats['time_last']))))
        lines.append(TEMPLATE % ('Total sailing time',
                                 timedelta(seconds=int(round(stats['time_last'] -
                                           stats['time_first'])))))
        lines.append('')
        lines.append('DISTANCES')
        lines.append(TEMPLATE % ('Sailed distance',
                                 conv('distance', stats['dist_total'])))
        lines.append(TEMPLATE % ('Furthest point',
                                 conv('distance', stats['dist_furthest'])))
        lines.append('')
        lines.append('SPEEDS')
        lines.append(TEMPLATE % ('Average speed',
                                 conv('speed', stats['speed_avg'])))
        lines.append(TEMPLATE % ('Top speed',
                                 conv('speed', stats['speed_max'])))
        lines.append('')
        lines.append('#' * len(lines[1]))
        lines.append('')
        for line in lines:
            print line

    def _plot(self, log):
        '''
        Plot graphs.
        '''
        log.plot()


    def _export(self, log, zip):
        '''
        Export a to KML / KMZ files.
        '''
        xml = geolib.get_kml(log)
        if zip:
            fname = log.fname + '.kmz'
            f = zipfile.ZipFile(fname, 'w')
            f.writestr('doc.kml', xml)
            f.close()
        else:
            fname = log.fname + '.kml'
            f = open(fname, 'w')
            f.write(xml)
            f.close()


if __name__ == '__main__':
    import argparse
    CommandLine()
