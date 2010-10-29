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
SEND_ACTUAL_HEADING       =  "h"

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