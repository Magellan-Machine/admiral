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

# Others
ON                        = 1
WIFI_MAYBE_LOST           = 5      # in seconds
WIFI_CONSIDER_LOST        = 10     # in seconds
WIFI_PORT                 = 5000
LOG_RAW_FNAME             = "../data/raw.log"
LOG_DB_FNAME              = "../data/log.sqlite"
LOG_CLEAN_FNAME           = "../data/clean.log"

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
            'T' : ('last_msg_millis', 'ms', 'INTEGER'),
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
