#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
Created on 9 Sep 2010

@author: Mac Ryan

Program to monitor and remotely control CircumSail, the autonomous sailing
robot. The program uses serial communication to interact with the onboard 
Arduino. 
'''


import serial
import gobject, gtk
from time import time
from graphics import *
from commons import *

# -----------------------------------------------------------------------------
# --- CLASSES
# -----------------------------------------------------------------------------

class Boat(object):
    
    '''
    Provide the logic interface to interact with the boat.
    '''
    
    def __init__(self, port='/dev/ttyUSB0', rate=115200):
        self.ser = serial.Serial(port, rate)
        self.ser.flush()
        self.log_char_mapping = {       # values used to decode log strings
            "R" : "rudder_position",
            "S" : "sail_position",
            "P" : "pilot_mode",
            "H" : "desired_heading",
        }
        for a in self.log_char_mapping.itervalues():
            setattr(self, a, 0)
        self.last_ping_time = 0
        self.send_command(SET_LOG_INTERVAL, 0)
    
    def send_command(self, *args):
        '''
        Send a command to the ship.
        
        Commands are a sequence of integers, the 
        first integer represents the command (see the constant section of this
        file), other parameters can represent different values (such intervals
        in seconds, heading in degrees, etc...).
        '''
        self.ser.write(' '.join(map(str, args)) + "\r")
        
    def poll_message(self):
        '''
        Retrieve and process a message from the ship (if available).
        
        Messages are strings concluded by a carriage return (ascii decimal 13).
        Messages can either be human readable (for debugging or informative
        purposes) or raw data for the logging system. The latter are prefixed
        with an exclamation mark ("!").
        '''
        if not self.ser.inWaiting():
            return
        msg = self.ser.readline().strip()
        if msg in (None, ""):
            return
        elif msg[0] != "!":
            return msg
        else:
            self.parse_log_data(msg[1:])
            return

    def parse_log_data(self, data):
        '''
        Update internal data on the boat
        '''
        for value in data.split():
            key, value = value.split(":")
            setattr(self, self.log_char_mapping[key], int(value))
        self.last_ping_time = time()


class ControlPanel(object):
    
    '''
    Provide the visual environment for interacting with the boat.
    '''
    
    def __init__(self, boat):
        self.boat = boat
        
        builder = gtk.Builder()
        builder.add_from_file("../data/gui.xml")
        builder.connect_signals(self)
        
        self.messages = builder.get_object("messages")
        self.command_line = builder.get_object("command")
        self.rudder_adjustment = builder.get_object("rudder_adjustment")
        self.sail_adjustment = builder.get_object("sail_winch_adjustment")
        self.logging_adjustment = builder.get_object("logging_interval_adjustment")
        
        # This was a placeholder widget to make editing in Glade easier
        tmp = builder.get_object("drawingarea")
        tmp.destroy()
                
        self.scene = Scene(boat)
        box = builder.get_object("frame1")
        box.add(self.scene)
        
        self.window = builder.get_object("window")
        self.window.set_size_request(640,480)
        self.window.show_all()
        
        gobject.timeout_add(10, self.serial_monitor)
        gobject.timeout_add(30, self.scene.redraw)
        
        self.on_ms_radio_toggled(None) # Initialise the values
    
    def serial_monitor(self):
        msg = self.boat.poll_message()
        if msg :
            self.messages.set_text(msg)
        if self.boat.pilot_mode != COMPUTER:   # Avoid infinite loop
            self.sail_adjustment.set_value(self.boat.sail_position)
            self.rudder_adjustment.set_value(self.boat.rudder_position)
        return True    #Necessary to keep it being scheduled by GObject
    
    def on_window_destroy(self, widget, data=None):
        gtk.main_quit()

    def on_command_button_clicked(self, widget, data=None):
        self.boat.send_command(self.command_line.get_text())
 
    def on_set_log_speed_button_clicked(self, widget, data=None):
        tmp = self.logging_adjustment
        self.boat.send_command(SET_LOG_INTERVAL, int(tmp.value*tmp.multiplier))
    
    def on_stop_logging_button_clicked(self, widget, data=None):
        self.boat.send_command(SET_LOG_INTERVAL, 0)
    
    def on_ms_radio_toggled(self, widget, data=None):
        a = self.logging_adjustment
        a.value          = 100
        a.lower          = 100
        a.upper          = 1000
        a.step_increment = 50
        a.multiplier      = -1
    
    def on_s_radio_toggled(self, widget, data=None):
        a = self.logging_adjustment
        a.value          = 1
        a.lower          = 1
        a.upper          = 60
        a.step_increment = 1
        a.multiplier      = 1
        
    def on_m_radio_toggled(self, widget, data=None):
        a = self.logging_adjustment
        a.value          = 1
        a.lower          = 1
        a.upper          = 60
        a.step_increment = 1
        a.multiplier      = 1000
    
    def on_rc_button_toggled(self, widget, data=None):
        self.boat.send_command(SET_PILOT_MODE, RC)

    def on_autopilot_button_toggled(self, widget, data=None):
        self.boat.send_command(SET_PILOT_MODE, AUTO)
    
    def on_computer_pilot_button_toggled(self, widget, data=None):
        self.boat.send_command(SET_PILOT_MODE, COMPUTER)
               
    def on_off_pilot_button_toggled(self, widget, data=None):
        self.boat.send_command(SET_PILOT_MODE, OFF)
        
    def on_sail_winch_adjustment_value_changed(self, widget, data=None):
        if self.boat.pilot_mode != COMPUTER:
            return # Avoid an infinite loop
        self.boat.send_command(SET_SAIL, widget.get_value())
    
    def on_rudder_adjustment_value_changed(self, widget, data=None):
        if self.boat.pilot_mode != COMPUTER:
            return # Avoid an infinite loop
        self.boat.send_command(SET_RUDDER, widget.get_value())
    
# -----------------------------------------------------------------------------
# --- MAIN PROGRAM
# -----------------------------------------------------------------------------

if __name__ == '__main__':
    app = ControlPanel(Boat())
    gtk.main()