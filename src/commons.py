# -*- coding: utf-8 -*-
'''
Created on 15 Sep 2010

@author: Mac Ryan

@file: Common imports and constant definitions.
'''

# -----------------------------------------------------------------------------
# --- COMMON IMPORT TO ALL MODULES
# -----------------------------------------------------------------------------

from time import time
import math

# -----------------------------------------------------------------------------
# --- CONSTANTS
# -----------------------------------------------------------------------------

# Commands
SET_LOG_INTERVAL          =  "I"
SET_PILOT_MODE            =  "P"
SET_HEADING               =  "H"
SET_RUDDER                =  "R"
SET_SAIL                  =  "S"

# Values for pilot mode
OFF                       = 0
AUTO                      = 1
RC                        = 2
COMPUTER                  = 3

# Colours
WATER                     = "#009AD6"
COMPUTER_CONTROLLED       = "#D70019"

# Lockscreen widget
LS_NOTCH_W = 80
LS_COLORS = ("#A00", "#0A0")
LS_TEXT = ("Slide to unlock", "Slide to lock")

# Others
ON                        = 1
WIFI_MAYBE_LOST           = 5      # in seconds
WIFI_CONSIDER_LOST        = 10     # in seconds
WIFI_PORT                 = 5000
LOG_RAW_FNAME             = "../data/raw.log"
LOG_DB_FNAME              = "../data/log.sqlite"
LOG_CLEAN_FNAME           = "../data/clean.log"
STINT_MINIMUM_LENGTH      = 30     # in seconds
STINT_MAX_STILL_TIME      = 5      # in seconds 
STINT_SPEED_THRESHOLD     = 0.1    # in m/s
EARTH_RADIUS              = 6371   # in Km

# Log signals are used to parse log data from the boat into the log system
# Each entry in the dictionary should be read like this contains:
# Key:    - the letter used in the string coming from the boat
# Value:  - the name of the boat property that should hold the actual value
#           this name is also used to generate coloumn names for storing
#           the log in the DB
#         - the unit of measure (usde for the numerical monitor)
#         - the sqlite type (used to generate db tables)
LOG_SIGNALS = {
            'A' : ('bat_absorption', 'µA', 'INTEGER'),
            'B' : ('bat_timeleft', 's', 'INTEGER'),
            'H' : ('desired_heading', '°', 'INTEGER'),
            'N' : ('north', '°', 'INTEGER'),
            'P' : ('pilot_mode', 'CODE', 'INTEGER'),
            'R' : ('rudder_position', '%', 'INTEGER'),
            'S' : ('sail_position', '%', 'INTEGER'),
            'T' : ('ardu_millis', 'ms', 'INTEGER'),
            'X' : ('longitude', '°', 'REAL'),
            'Y' : ('latitude', '°', 'REAL'),
            'W' : ('relative_wind', '°', 'INTEGER'),
            'I' : ('log_signal_interval', 'ms', 'INTEGER'),

            'n' : ('magnetic_north', '°', 'INTEGER'),     # TODO: Remove when accel on arduino
            'x' : ('magnetic_x', '-', 'INTEGER'),         # TODO: Remove when accel on arduino
            'y' : ('magnetic_y', '-', 'INTEGER'),         # TODO: Remove when accel on arduino
            'z' : ('magnetic_z', '-', 'INTEGER'),         # TODO: Remove when accel on arduino
            
            'a' : ('accelerometer_x', '-', 'INTEGER'),    # TODO: Remove when accel on arduino
            'b' : ('accelerometer_y', '-', 'INTEGER'),    # TODO: Remove when accel on arduino
            'c' : ('accelerometer_z', '-', 'INTEGER'),    # TODO: Remove when accel on arduino
            
            'u' : ('ardu_used_voltage', 'mV', 'INTEGER'),
            'i' : ('ardu_used_current', 'mA', 'INTEGER'),
            'p' : ('ardu_used_power', 'mW', 'INTEGER'),
            'e' : ('ardu_energy_counter', 'µJ', 'INTEGER'),
        }

# -----------------------------------------------------------------------------
# --- HELPER FUNCTIONS
# -----------------------------------------------------------------------------

def gps_distance_between(point_a, point_b):
    '''
    Calculate the orthodromic distance between two GPS readings.
   
    point_a and point_b can be either of the two:
    - tuples in the form (latitude, longitude).
    - instances of the class logwork.Signal
    The result is in metres.
    
    ATTENTION: since latitude is given before longitude, if we are using the 
    X and Y representation, then we must pass in (Y, X) and *not* (X, Y)
    
    Computed with the Haversine formula 
    (http://en.wikipedia.org/wiki/Haversine_formula)
    '''
    if hasattr(point_a, 'latitude'):
        a_lat, a_lon = math.radians(point_a.latitude), math.radians(point_a.longitude)
    else:
        a_lat, a_lon = math.radians(point_a[0]), math.radians(point_a[1])
    if hasattr(point_b, 'latitude'):
        b_lat, b_lon = math.radians(point_b.latitude), math.radians(point_b.longitude)
    else:
        b_lat, b_lon = math.radians(point_b[0]), math.radians(point_b[1])
    d_lat = b_lat - a_lat
    d_lon = b_lon - a_lon
    a = math.sin(d_lat/2.0)**2 + math.cos(a_lat) * math.cos(b_lat) * math.sin(d_lon/2.0)**2
    c = 2 * math.asin(math.sqrt(a))
    return EARTH_RADIUS * c * 1000