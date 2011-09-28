#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Provide a mini-touch-screen-friendly GUI for doing routine operations on the
OpenMoko FreeRunner.
'''

__author__ = "Mac Ryan (mac@magellanmachine.se)"
__created__ = "2010/09/25"
__copyright__ = "Copyright (c) 2010 The Magellan Machinep"
__license__ = "GPLv3 - http://www.gnu.org/licenses/gpl.html"


import gtk

from freerunner import FreeRunner

class FreeRunnerControlPanel(object):

    '''
    Provide the visual environment for interacting with the boat.
    '''

    def __init__(self):
        # Various
        self.fr = FreeRunner()
        self.network_index = -1

        # GTK building
        builder = gtk.Builder()
        builder.add_from_file("../data/freerunner-utility.xml")
        builder.connect_signals(self)
        self.pwr_toggle     = builder.get_object("pwr_toggle")
        self.usb_toggle     = builder.get_object("usb_toggle")
        self.op_in_progress = builder.get_object("op_in_progress")
        self.window         = builder.get_object("window")

        # Button extension and initialisation
        self.usb_toggle.fr_attribute = "usb_mode"
        self.usb_toggle.alternatives = (('I am a DEVICE', 'device'),
                                        ('I am a HOST', 'host'))
        self.usb_toggle.set_active(self.fr.usb_mode.strip() == 'host')
        self.toggler(self.usb_toggle)
        self.pwr_toggle.fr_attribute = "power_mode"
        self.pwr_toggle.alternatives = (('I am GIVING energy to USB', 1),
                                        ('I am TAKING energy via USB', 0))
        self.pwr_toggle.set_active(self.fr.power_mode.strip() == '0')
        self.toggler(self.pwr_toggle)

        # Showtime!
        self.window.maximize()
        self.window.show()

    def toggler(self, widget):
        '''
        Helper method that connects a toggle button to a FreeRunner propriety

        each toggable widget has a "fr_attribute" and two couples of
        button_label/attr_value, the first of which refers to the
        "button up" state.
        '''
        label, value = widget.alternatives[widget.get_active()]
        setattr(self.fr, widget.fr_attribute, value)
        widget.set_label(label)

    def throbber(self, func):
        '''
        Helper method that execute a routine while displaying a "throbber"
        '''
        self.op_in_progress.show_all()
        # make sure the throbbing starts now
        while gtk.events_pending():
            gtk.main_iteration()
        try:
            func()
        finally:
            self.op_in_progress.hide()

    def on_usb_toggle_toggled(self, widget):
        self.toggler(widget)

    def on_power_toggle_toggled(self, widget):
        self.toggler(widget)

    def on_window_destroy(self, widget, data=None):
        gtk.main_quit()

    def on_quit_clicked(self, widget):
        gtk.main_quit()


if __name__ == '__main__':
    app = FreeRunnerControlPanel()
    gtk.main()
