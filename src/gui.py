# -*- coding: utf-8 -*-
'''
Created on 28 Sep 2010

@author: Mac Ryan

@file: Provide context-aware GUI's for interacting with the program.
'''

import gobject, gtk
import boat
from commons import *
from graphics import Scene
from time import time
from freerunner import FreeRunner

class GeneralControlPanel(object):
    
    '''
    Abstract class that serves as an ancestor for the computer e freerunner
    specific interfaces.
    '''

    def __init__(self):
        '''
        Boilerplate init code, should NOT be overridden but extended.
        '''
        self.builder = gtk.Builder()
        self.builder.add_from_file(self.gui_file)
        self.builder.connect_signals(self)
        self.window = self.builder.get_object("window")
        self.logfile = open('../data/raw_msg.log', 'a', -1)
        self.last_logged_msg = None;
        
    def do_log(self):
        if self.boat.last_msg != self.last_logged_msg:
            self.logfile.write(str(time()) + " " + self.boat.last_msg + "\n")
            self.last_logged_msg = self.boat.last_msg
    
    def on_window_destroy(self, widget, data=None):
        '''
        Works as far as you follow conventions...
        '''
        gtk.main_quit()
        

class ComputerControlPanel(GeneralControlPanel):
    
    '''
    Provide the visual environment for interacting with the boat from the PC.
    '''
    
    def __init__(self):
        self.boat = boat.BareBoat()
        self.gui_file = "../data/computer-gui.xml"
        super(ComputerControlPanel, self).__init__()

        self.messages = self.builder.get_object("messages")
        self.command_line = self.builder.get_object("command")
        self.rudder_adjustment = self.builder.get_object("rudder_adjustment")
        self.sail_adjustment = self.builder.get_object("sail_winch_adjustment")
        self.logging_adjustment = self.builder.get_object("logging_interval_adjustment")
        
        # The following bit replace the placeholder drawing area with the scene
        tmp = self.builder.get_object("drawingarea")
        tmp.destroy()        
        self.scene = Scene(self.boat)
        box = self.builder.get_object("frame1")
        box.add(self.scene)
        
        gobject.timeout_add(10, self.serial_monitor)
        gobject.timeout_add(30, self.scene.redraw)        
        self.on_ms_radio_toggled(None) # Initialise the values

        self.window.set_size_request(640,480)
        self.window.show_all()
    
    def serial_monitor(self):
        msg = self.boat.poll_message()
        if msg != None and msg[0] != '!':
            self.messages.set_text(msg)
        if self.boat.pilot_mode != COMPUTER:   # Avoid infinite loop
            self.sail_adjustment.set_value(self.boat.sail_position)
            self.rudder_adjustment.set_value(self.boat.rudder_position)
        return True    #Necessary to keep it being scheduled by GObject

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


class FreeRunnerControlPanel(GeneralControlPanel):

    def __init__(self):
        self.fr = FreeRunner()
        self.boat = boat.FreeBoat(freerunner=self.fr)
        self.gui_file = "../data/freerunner-gui.xml"
        super(FreeRunnerControlPanel, self).__init__()
        # Each subsystem has its name, name in self.active_system
        # set indicates the system is active. self.active_systems is passed
        # to the instance of FreeRunner. All systems are initially OFF
        self.active_systems = set() 
        self.run_mode = False
        self.logging_mode = False
        gobject.timeout_add(10, self.loop)
        self.window.maximize()
        self.window.show_all()

    def loop(self):
        '''
        Executes callbacks if the program is in runmode (button on the GUI)
        '''
        if self.run_mode == True:
            msg = self.boat.poll_message(self.active_systems)
            if self.logging_mode:
                self.do_log()
        return True    #Necessary to keep it being scheduled by GObject

    def _subsystem(self, subsystem, widget):
        '''
        Helper function to manage the self.active_systems record
        '''
        if widget.get_active():
            self.active_systems.add(subsystem)
        else:
            self.active_systems.remove(subsystem)

    def on_run_button_toggled(self, widget):
        self.run_mode = widget.get_active()
        if self.run_mode:
            self.boat.send_command(SET_LOG_INTERVAL, 3)
        else:
            self.boat.send_command(SET_LOG_INTERVAL, 0)

    def on_use_accelerometer_toggled(self, widget):
        self._subsystem('accelerometer', widget)

    def on_use_gps_toggled(self, widget):
        self._subsystem('GPS', widget)
        if widget.get_active():
            self.fr.gps_up()
        else:
            self.fr.gps_down()

    def on_wireless_watchdog_toggled(self, widget):
        self._subsystem('watchdog', widget)

    def on_wireless_input_toggled(self, widget):
        self._subsystem('wifi_in', widget)

    def on_wireless_output_toggled(self, widget):
        self._subsystem('wifi_out', widget)

    def on_log_data_toggled(self, widget):
        self.logging_mode = widget.get_active()
        