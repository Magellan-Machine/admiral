# -*- coding: utf-8 -*-
'''
Created on 28 Sep 2010

@author: Mac Ryan

@file: Provide context-aware GUI's for interacting with the program.
'''

import gobject, pango, gtk
import boat, wifibridge
from commons import *
from graphics import Scene
from time import time
from freerunner import FreeRunner


class NumericMonitor(object):
    
    '''
    Generate a window showing all the proprieties of the boat.
    '''
    
    def __init__(self, boat, menuitem):
        self.boat = boat
        self.menuitem = menuitem
        self.window = gtk.Window(gtk.WINDOW_TOPLEVEL)
        # Generate table
        cols = 5
        ceil = lambda a, b : a/b if not a%b else a/b + 1
        rows = ceil(len(LOG_SIGNALS), cols)
        table = gtk.Table(cols, rows, True)
        self.window.add(table)
        # Populate the table
        self.textboxes = {}
        for ordinal, property in enumerate(LOG_SIGNALS, 0):
            if ordinal != 0:
                col = ordinal % cols
                row = ordinal / cols
            else:
                col, row = 0, 0
            # Cell
            cell = gtk.VBox(False, 0)
            cell.set_border_width(8)
            # First row: label
            label = gtk.Label()
            label.set_alignment(1, 0.5)
            label.set_ellipsize(pango.ELLIPSIZE_END)
            label.set_markup('<b>' + LOG_SIGNALS[property][0] + '</b>')
            label.set_tooltip_text(LOG_SIGNALS[property][0])
            cell.pack_start(label)
            # Second row: Hbox with value and units
            entry = gtk.HBox(False, 0)
            entry.set_border_width(2)
            value = gtk.Entry(10)
            value.set_width_chars(15)
            value.set_alignment(gtk.JUSTIFY_RIGHT)
            value.set_editable(False)
            entry.pack_start(value)
            units = gtk.Label()
            units.set_markup('<i>' + LOG_SIGNALS[property][1] + '</i>')
            entry.pack_start(units)
            cell.pack_start(entry)
            table.attach(cell, col, col+1, row, row+1, gtk.FILL, gtk.FILL)
            self.textboxes[property] = value
        # Tune the window
        self.window.set_title("Numeric Monitor")
        self.window.set_border_width(10)
        self.window.resize(1, 1)
        self.window.set_resizable(False)
        self.window.connect("delete_event", self.on_nm_delete)
        self.window.show_all()
        
    def update_values(self):
        for k in self.textboxes.keys():
            value = getattr(self.boat, LOG_SIGNALS[k][0])
            self.textboxes[k].set_text(str(value))

    def on_nm_delete(self, widget, data=None):
        self.window.hide()
        self.menuitem.set_active(False)
        return True


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
        self.logfile = open(LOG_RAW_FNAME, 'a', 1)
        self.last_logged_msg = None
        
    def do_log(self):
        if self.boat.last_msg != self.last_logged_msg:
            self.logfile.write(str(time()) + " " + self.boat.last_msg + "\n")
            self.last_logged_msg = self.boat.last_msg
    
    def on_window_destroy(self, widget):
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
        self.remote_uri_dialogue = self.builder.get_object("remote_boat_win_dialogue")
        self.remote_ip_widget = self.builder.get_object("remote_ip")
        self.remote_port_widget = self.builder.get_object("remote_port")
        self.about_dialogue = self.builder.get_object("about_dialogue")
        
        # The following bit replace the placeholder drawing area with the scene
        tmp = self.builder.get_object("drawingarea")
        tmp.destroy()
        self.scene = Scene(self.boat)
        box = self.builder.get_object("frame1")
        box.add(self.scene)
        
        gobject.timeout_add(10, self.serial_monitor)
        gobject.timeout_add(30, self.scene.redraw)
        self.on_ms_radio_toggled(None) # Initialise the values

        # Other varaibles
        self.logging_mode = False
        self.nm = None

        self.window.resize(900, 640)
        self.window.show_all()
    
    def serial_monitor(self):
        msg = self.boat.poll_message()
        if msg != None and msg[0] != '!':
            self.messages.set_text(str(msg))
            if self.debug_mode:
                print ">>> ", msg
        if self.boat.pilot_mode != COMPUTER:   # Avoid infinite loop
            self.sail_adjustment.set_value(self.boat.sail_position)
            self.rudder_adjustment.set_value(self.boat.rudder_position)
        if self.logging_mode == True:
            self.do_log()
        if self.nm:
            self.nm.update_values()
        return True    #Necessary to keep it being scheduled by GObject

    def on_command_button_clicked(self, widget):
        self.boat.send_command(self.command_line.get_text())
 
    def on_set_log_speed_button_clicked(self, widget):
        tmp = self.logging_adjustment
        self.boat.send_command(SET_LOG_INTERVAL, int(tmp.value*tmp.multiplier))
    
    def on_stop_logging_button_clicked(self, widget):
        self.boat.send_command(SET_LOG_INTERVAL, 0)
    
    def on_ms_radio_toggled(self, widget):
        a = self.logging_adjustment
        a.value          = 100
        a.lower          = 100
        a.upper          = 1000
        a.step_increment = 50
        a.multiplier      = -1
    
    def on_s_radio_toggled(self, widget):
        a = self.logging_adjustment
        a.value          = 1
        a.lower          = 1
        a.upper          = 60
        a.step_increment = 1
        a.multiplier      = 1
        
    def on_m_radio_toggled(self, widget):
        a = self.logging_adjustment
        a.value          = 1
        a.lower          = 1
        a.upper          = 60
        a.step_increment = 1
        a.multiplier      = 1000
    
    def on_rc_button_toggled(self, widget):
        self.boat.send_command(SET_PILOT_MODE, RC)

    def on_autopilot_button_toggled(self, widget):
        self.boat.send_command(SET_PILOT_MODE, AUTO)
    
    def on_computer_pilot_button_toggled(self, widget):
        self.boat.send_command(SET_PILOT_MODE, COMPUTER)
               
    def on_off_pilot_button_toggled(self, widget):
        self.boat.send_command(SET_PILOT_MODE, OFF)
        
    def on_sail_winch_adjustment_value_changed(self, widget):
        if self.boat.pilot_mode != COMPUTER:
            return # Avoid an infinite loop
        self.boat.send_command(SET_SAIL, widget.get_value())

    def on_rudder_adjustment_value_changed(self, widget):
        if self.boat.pilot_mode != COMPUTER:
            return # Avoid an infinite loop
        self.boat.send_command(SET_RUDDER, widget.get_value())

    def on_logg_on_off_button_toggled(self, widget):
        state = widget.get_active()
        self.logging_mode = state
        widget.set_label("Logging in ON" if state else "Logging is OFF")

    def on_connect_remote_button_clicked(self, widget):
        if self.remote_ip_widget.get_text() == '':
            self.remote_ip_widget.set_text('192.168.1.35')
        if self.remote_port_widget.get_text() == '':
            self.remote_port_widget.set_text('5000')
        self.remote_uri_dialogue.show()
        
    def on_remote_boat_win_dialogue_delete_event(self, widget):
        widget.hide_on_delete()
        return True
        
    def on_boat_uri_button_clicked(self, widget):
        host = self.remote_ip_widget.get_text()
        port = int(self.remote_port_widget.get_text())
        try:
            remote_boat = boat.RemoteBoat((host, port))
        except Exception as e:
            print "Failed to connect: ", e
        else:
            self.boat = remote_boat
            self.remote_uri_dialogue.hide()
            self.scene.change_boat(self.boat)
        
    def on_disconnect_menu_item_activate(self, widget):
        print "disconnect"
        
    def on_log_activate_item(self, widget):
        print "log"
        
    def on_wifi_activate_item(self, widget):
        print "wifi"
        
    def on_serial_activate_item(self, widget):
        print "serial"
        
    def on_about_menu_item_activate(self, widget):
        self.about_dialogue.show()
        
    def on_about_dialogue_delete_event(self, widget):
        self.about_dialogue.hide()
        return True

    def on_about_dialogue_response(self, widget):
        self.about_dialogue.hide()
        
    def on_numeric_monitor_toggled(self, widget):
        if widget.get_active():
            if self.nm == None:
                self.nm = NumericMonitor(self.boat, widget)
            else:
                self.nm.window.show_all()
        else:
            self.nm.window.hide()

    def on_debug_mode_toggled(self, widget):
        self.debug_mode = widget.get_active()
        
        
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
        self.wifi = None
        self.watchdog = False
        gobject.timeout_add(10, self.loop)
        self.window.maximize()
        self.window.show_all()

    def loop(self):
        '''
        Executes callbacks if the program is in runmode (button on the GUI)
        '''
        if self.run_mode == True:
            # WiFi ops (including Watchdog) 
            if self.wifi:
                wifi_msg = self.wifi.read()
                if wifi_msg:
                    self.boat.send_command(wifi_msg) 
                if self.wifi.remote_address:
                    if self.last_sent_wifi_message != self.boat.last_msg:
                        self.wifi.write(self.boat.last_msg)
                        self.last_sent_wifi_message = self.boat.last_msg
                    elapsed = time() - self.wifi.last_wifi_in_time
                    if self.watchdog and WIFI_MAYBE_LOST < elapsed:
                        self.wifi.ping()
                        if WIFI_CONSIDER_LOST < elapsed:
                            self.boat.send_command(SET_PILOT_MODE, RC)
                            self.wifi = None
            # Logging ops
            if self.logging_mode:
                self.do_log()
            # Pll message
            self.boat.poll_message(self.active_systems)
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

    def on_battery_info_toggled(self, widget):
        self._subsystem('battery_info', widget)
        
    def on_wireless_watchdog_toggled(self, widget):
        self.watchdog = True if widget.get_active() else False

    def on_wireless_bridge_toggled(self, widget):
        if widget.get_active():
            self.wifi = wifibridge.WifiBridge()
            self.last_sent_wifi_message = ''
        else:
            self.wifi = None

    def on_log_data_toggled(self, widget):
        self.logging_mode = widget.get_active()
