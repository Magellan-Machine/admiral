# -*- coding: utf-8 -*-
'''
Provide the logic interface to interact with the boat.
'''

import serial
import random
import logging
from time import time

import gobject

__author__ = "Mac Ryan"
__copyright__ = "Copyright ©2011, Mac Ryan"
#__credits__ = ["Name Lastname", "Name Lastname"]
__license__ = "GPL v3"
#__version__ = "<dev>"
#__date__ = "<unknown>"
__maintainer__ = "Mac Ryan"
__email__ = "quasipedia@gmail.com"
__status__ = "Development"

log = logging.getLogger('general.arduino')


class MockSerial(object):

    '''
    Mock class that implements some of the serial.Serial methods.

    This is used for testing the programme when the computer or the freerunner
    are not connected to the Arduino board.
    '''

    # Properties use the logging string as key, and the following list of
    # data as values: extended_name, range(min, max, step)
    REGISTERED_PROPERTIES = dict(
         R = ['rudder', [500, 2500, 5]],
         S = ['sail', [500, 2500, 5]])
    # Interval between device log messages, in seconds
    INTERVAL = 0.1

    def __init__(self):
        self.last_msg_time = 0
        self.__values = {}
        for k, (name, range_) in self.REGISTERED_PROPERTIES.items():
            self.__values[k] = random.randrange(*range_)
        self.__log_lines = []
        gobject.timeout_add(200, self._update)

    def _update(self):
        '''
        Sweep values of the mock serial.
        '''
        if time() - self.last_msg_time > self.INTERVAL:
            self._update_values()
            self._prepare_line()
        return True  #needed for keeping in gobject loop!

    def _update_values(self):
        '''
        Update the values of the simulated sensors.
        '''
        for k, (name, range_) in self.REGISTERED_PROPERTIES.items():
            min_, max_, step = range_
            current = self.__values[k]
            if current + step > max_ or current + step < min_:
                step *= -1
                range_[2] = step
            self.__values[k] += step

    def _prepare_line(self):
        '''
        Returns an arduino-like log message.
        '''
        msg = ','.join([k + str(v) for k, v in self.__values.items()]) + '\r'
        self.__log_lines.append(msg)
        self.last_msg_time = time()

    def readline(self, *arg, **kwargs):  #@UnusedVariable
        '''
        Emulate PySerial ``readline()`` method.
        '''
        return self.__log_lines.pop()

    def flushInput(self):
        '''
        Emulate flushing the queued data.
        '''
        self.__log_lines = []

    def inWaiting(self):
        '''
        Emulate PySerial ``inWaiting()`` method.
        '''
        return True if self.__log_lines else False


class Arduino(object):

    '''
    Interface to the Arduino relaying the information from the boat sensors.
    If the device is not found, a mock one is initialised anyhow.
    '''

    def __init__(self, port='/dev/ttyUSB0', rate=115200):
        try:
            # Arduino reset time need to be taken in account
            # (use 120m resistor to prevent this)
            start = time()
            log.debug('Trying to initialise Arduino @ %s' % start)
            self.serial = serial.Serial(port, rate, timeout=3)
            log.debug('Initialisation of Arduino done in %s seconds' %
                      (time() - start))
            msg = 'An arduino has been found on USB0 - Connecting.'
            self.boat_is_connected = True
            log.info(msg)
        except serial.SerialException:
            msg = 'Arduino not found - starting MOCK SERIAL communication!'
            log.info(msg)
            self.boat_is_connected = False
            self.serial = MockSerial()
        self.last_message = ''

    def poll_message(self):
        '''
        If available, retrieve a message from the Arduino. Messages are strings
        ended by a carriage return (ascii decimal 13) and a newline.
        '''
        # Early exit if no message is waiting
        log.debug('Going to read a serial line.')
        while self.serial.inWaiting():
            # Discards old data by consuming till the last line of buffer
            msg = self.serial.readline().strip()
        log.debug('Serial line read: %s' % msg)
        if msg:
            self.last_message = msg
            return msg
        return None

    def flush(self):
        '''
        Discard all serial data waiting to be read in the buffer.
        '''
        self.serial.flushInput()