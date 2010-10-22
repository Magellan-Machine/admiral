'''
Created on 28 Sep 2010

@author: mac

@file: Provide the logic interface to interact with the boat.
'''

import serial
from commons import *
from math import degrees, atan2
from time import sleep, time


class MockSerial(object):

    '''
    Mock class that implements some of the serial.Serial methods.
    
    This is used for testing the programme when the computer or the freerunner
    are not connected to the Arduino board. 
    '''
    
    def __init__(self):
        print "Arduino device not found - starting MOCK SERIAL COMMUNICATION!"
        self.values = {
            "I" : 0,
            "H" : 0,
            "P" : OFF,
            "R" : 0,
            "S" : 0,
            "T" : 0,
            "W" : 0,

            "n" : 0,     # TODO: Remove when accel on arduino
            "x" : 100,         # TODO: Remove when accel on arduino
            "y" : 0,         # TODO: Remove when accel on arduino
            "z" : 0,         # TODO: Remove when accel on arduino
        }
        self.steps = {
            'R' : 5,
            'S' : 5,
            'W' : 4,
            'x' : 3,
            'y' : 3,
        }
        self.last_inwaiting = 0
    
    def _step(self, key, lo, hi, fish):
        '''Rotate or swing arduino values progressively.
        
        "key"         is the key of the value to alter [as in arduino messages]
        "lo" and "hi" are the boundaries of the movement
        "fish"        indicate if the direction of movement must revert once a
                      limit has been hit
        '''
        assert lo < hi
        value = self.values[key]
        value += self.steps[key]
        if value < lo:
            value = lo
            if fish:
                self.steps[key] *= -1
        if value > hi:
            value = hi
            if fish:
                self.steps[key] *= -1
        if not fish:
            assert lo == 0
            value %= hi
        return value

    def write(self, string):
        '''
        Strings passed to this method are in the form "X value".
        '''
        k, v = string.split()
        v = int(float(v))
        if k == 'I' and v < 0:     # This needs processing as on the arduino!
            v *= -0.001
        self.values[k] = v
    
    def readline(self):
        '''
        Returns an arduino-like log message.
        
        Values are either echoed from last input, or simulated pseudo-randomly.
        '''
        if self.values['P'] == AUTO:
            self.values['R'] = self._step('R', -100, 100, True)
            self.values['S'] = self._step('S', 0, 100, True)
            self.values['W'] = self._step('W', 0, 360, False)
            self.values['x'] = self._step('x', -100, 100, True)
            self.values['y'] = self._step('y', -100, 100, True)
            self.values['n'] = int(
                (degrees(atan2(self.values['x'], self.values['y'])) + 270) % 360)
        self.values['T'] = int(time()*1000)
        msg = '!'
        for k, v in self.values.items():
            msg += k + ':' + str(v) + ' '
        self.last_inwaiting = time()
        return msg + "\r"
    
    def inWaiting(self):
        if self.values['I'] == 0:
            return False
        return True if (time() - self.last_inwaiting) > self.values['I'] else False

class BareBoat(object):
    
    '''
    BareBoat is the Arduino only boat.
    
    It is typically used by the FreeRunner, but can also used by a normal
    client. Provides access to all the Arduino-controlled devices and data.
    '''
    
    def __init__(self, port='/dev/ttyUSB0', rate=115200):
        try:
            self.ser = serial.Serial(port, rate)
            sleep(2)   # Arduino reset (use 120m resistor to prevent this)
        except serial.SerialException:
            self.ser = MockSerial()
        self.log_char_mapping = {       # values used to decode log strings
            "A" : "bat_absorption",
            "B" : "bat_timeleft",
            "H" : "desired_heading",
            "N" : "north",
            "P" : "pilot_mode",
            "R" : "rudder_position",
            "S" : "sail_position",
            "T" : "last_msg_millis",
            "X" : "longitude",
            "Y" : "longitude",
            "W" : "relative_wind",
            "I" : "log_signal_interval",

            "n" : "magnetic_north",     # TODO: Remove when accel on arduino
            "x" : "magnetic_x",         # TODO: Remove when accel on arduino
            "y" : "magnetic_y",         # TODO: Remove when accel on arduino
            "z" : "magnetic_z",         # TODO: Remove when accel on arduino
        }
        for a in self.log_char_mapping.itervalues():
            setattr(self, a, 0)
        self.coordinates = None
        self.last_ping_time = 0
        self.last_msg = ''
    
    def send_command(self, *args):
        '''
        Send a command to the ship.
        
        Commands are a sequence of integers, the 
        first integer represents the command (see the constant section of this
        file), other parameters can represent different values (such intervals
        in seconds, heading in degrees, etc...).
        '''
        self.ser.write(' '.join(map(str, args)) + "\r")
        
    def poll_message(self, auto_parse=True):
        '''
        Retrieve and process a message from the ship (if available).
        
        Messages are strings concluded by a carriage return (ascii decimal 13).
        Messages can either be human readable (for debugging or informative
        purposes) or raw data for the logging system. The latter are prefixed
        with an exclamation mark ("!").
        '''
        # Early exit if no message is waiting
        if not self.ser.inWaiting():
            return None
        # Early exit if the message is empty
        msg = self.ser.readline().strip()
        if msg in (None, ""):
            return None
        # If the message is there
        if msg[0] == '!' and auto_parse == True:
            self.parse_log_data(msg[1:])
        self.last_msg = msg
        return msg

    def parse_log_data(self, data):
        '''
        Update internal data on the boat
        '''
        for value in data.split():
            key, value = value.split(":")
            setattr(self, self.log_char_mapping[key], int(float(value)))
        self.last_ping_time = time()


class FreeBoat(BareBoat):
    
    '''
    FreeBoat is the Arduino+FreeRunner boat. 
    
    It is a boat typically used for remotely interacting with the 
    onboard FreeRunner. It merges in a single object the information that
    is controlled by both the Arduino and the FreeRunner.
    '''

    def __init__(self, port='/dev/ttyUSB0', rate=115200, freerunner=None):
        super(FreeBoat, self).__init__(port, rate)
        self.fr = freerunner

    def poll_message(self, subsystems, auto_parse=True):
        '''
        Add to the log messages the data provided by the FreeRunner.
        
        See docstring for the parent class for more details on the message
        sent by the Arduino. "subsystems" is a set indicating what subsystems
        are active on the FreeRunner (and should be therefore appended to
        the log message).
        '''
        # The auto_parse is left on because the accelerometer subsystem
        # needs the data from the magnetometer on the Arduino.
        msg = super(FreeBoat, self).poll_message(auto_parse=True)
        if msg != None and msg[0] == '!' :
            if 'accelerometer' in subsystems:
                self.north = self._compute_north_with_acc_data()
                msg += " N:" + str(self.north)
            if 'GPS' in subsystems:
                lat, lon = self.fr.get_gps()
                msg += " Y:" + str(lat)
                msg += " X:" + str(lon)
            if 'watchdog' in subsystems:
                pass
            if 'wifi_in' in subsystems:
                pass
            if 'wifi_out' in subsystems:
                pass
            if 'file_logging' in subsystems:
                pass
            msg += " A:" + str(self.fr.bat_absorption)
            msg += " B:" + str(self.fr.bat_timeleft)
            if auto_parse == True:
                self.parse_log_data(msg[1:])
            self.last_msg = msg
        return msg
            
    def _compute_north_with_acc_data(self):
        '''
        Compensate 3D magnetomer reading for tilt of the boat, via accelerometer.
        
        '''
        def normalise(vector):    #max length of a component = 1000
            ratio = 1000.0/max([abs(c) for c in vector])
            return [int(c*ratio) for c in vector]
        def cross_product(a, b):
            x = a[1]*b[2]-a[2]*b[1]
            y = a[2]*b[0]-a[0]*b[2]
            z = a[0]*b[1]-a[1]*b[0]
            return normalise((x, y, z))
        def vector_to_deg(vector):
            x, y, z = vector
            return degrees(atan2(x, y)) % 360
        a_vector = normalise(self.fr.accelerometer)
        m_vector = normalise((self.magnetic_x, self.magnetic_y, self.magnetic_z))
        east = cross_product(a_vector, m_vector)
        north = cross_product(a_vector, east)
        print "A:", a_vector, "   M:", m_vector, "   E:", east, "   N:", int(vector_to_deg(north)) 
        return int(vector_to_deg(north))
    