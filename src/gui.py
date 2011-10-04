# -*- coding: utf-8 -*-
'''
Provide the GUI elements for admiral.
'''

import logging
import serial
import termios
from time import time

import gtk, gobject  #@UnresolvedImport
from lib import graphics
from lib import pytweener as tween

from arduino import Arduino, MockSerial
from freerunner import FreeRunner
from blackbox import blackbox as bbox

__author__ = "Mac Ryan"
__copyright__ = "Copyright ©2011, Mac Ryan"
#__credits__ = ["Name Lastname", "Name Lastname"]
__license__ = "GPL v3"
#__version__ = "<dev>"
#__date__ = "<unknown>"
__maintainer__ = "Mac Ryan"
__email__ = "quasipedia@gmail.com"
__status__ = "Development"

# LOCKSCREEN WIDGET
LS_NOTCH_W = 80
LS_COLORS = ("#A00", "#0A0")
LS_TEXT = ("Slide to unlock", "Slide to lock")

#LOGGER
log = logging.getLogger('general.gui')


class FreeRunnerControlPanel(object):

    '''
    A touch-screen friendly control panel for the logging appllication.
    '''

    BBOX_INTERVAL = 1  #Seconds between bbox messages

    def __init__(self):
        self.builder = gtk.Builder()
        self.builder.add_from_file('../data/freerunner-gui.xml')
        self.builder.connect_signals(self)
        self.window = self.builder.get_object("window")
        self.gps_coords_label = self.builder.get_object('gps_coords_label')
        self.serial_link_label = self.builder.get_object('serial_link_label')
        self.log_size_label = self.builder.get_object('log_size_label')
        # Collect all buttons in order to be able to gray them out later on
        self.all_buttons=[]
        self.all_buttons.append(self.builder.get_object("quit_button"))
        self.all_buttons.append(self.builder.get_object("run_button"))
        # The following bit replace the placeholder drawing area with the scene
        tmp = self.builder.get_object("drawingarea")
        tmp.destroy()
        self.scene = LockScreen(self._set_button_sensitivity)
        box = self.builder.get_object("frame1")
        box.add(self.scene)
        # Initialise variables
        self.boat = Arduino()
        self.freerunner = FreeRunner()
        self.run_mode = False
        self.time_last_bbox_msg = 0
        self.last_bbox_msg = ''
        # Add callback to timed loop
        gobject.timeout_add(100, self.loop)
        # Dispaly the GUI
        self.window.maximize()
        self.window.show_all()

    def loop(self):
        '''
        Executes callbacks if the program is in runmode.
        Runmode = Button on the GUI is pressed.
        '''
        try:
            if self.run_mode == True:
                self._do_log()
            else:
                self.boat.flush()
        except (IOError, serial.SerialException,
                serial.SerialTimeoutException, termios.error) as e:
            msg = 'Serial connection lost. Falling back on mock serial. ' \
                  'Exception: %s' % e
            log.critical(msg)
            self.boat.boat_is_connected = False
            self.boat.serial = MockSerial()
        # ALWAYS RUN
        fix = self.freerunner.gps_fix
        if fix:
            text = 'Latitude: %.7f\nLongitude: %.7f' % fix
            ok = True
        else:
            text = 'No GPS fix'
            ok = False
        self.gps_coords_label.set_markup(self._to_markup(text, ok))
        # LOG entry counter
        if bbox.active:
            text = 'ID: %s\nLog size: %05d' % (bbox.active[0], bbox.lines)
            ok = True
        else:
            text = 'Tracker is offline'
            ok = False
        self.log_size_label.set_markup(self._to_markup(text, ok))
        # SERIAL STATUS
        if self.boat.boat_is_connected:
            text = 'Serial link is UP'
            ok = True
        else:
            text = 'Serial link is DOWN'
            ok = False
        self.serial_link_label.set_markup(self._to_markup(text, ok))

        # Force redraw (useful if MockSerial is hooked up to the gtk idle loop
        while gtk.events_pending():
            gtk.main_iteration()
        return True    #Necessary to keep it being scheduled by GObject

    def _do_log(self):
        '''
        Build and dump a log record.
        '''
        if time() - self.time_last_bbox_msg < self.BBOX_INTERVAL:
            return
        #FIXME: For now, we want all systems to be up and running to allow
        #       logging. This will change in the future.
        fix = self.freerunner.gps_fix
        if fix:
            # Acquire a boat message or exit.
            boat_message = self.boat.poll_message() or self.boat.last_message
            if not boat_message:
                return
            bits = []
            bits.append("Y%.7f,X%.7f" % fix)  #lat, lon
            bits.append("D%.2f" % self.freerunner.gps_hdop)  #HDOP
            bits.append("H%.2f,F%.2f" % self.freerunner.gps_moving) #head,speed
            bits.append(boat_message)
            bbox.log(','.join(bits))
            self.time_last_bbox_msg = time()

    def _to_markup(self, text, status):
        '''
        Helper function to make the text of a label bigger and coloured.
        ``text``: any string or unicode objects
        ``status``: True for OK and False for KO (translates to green and red)
        '''
        #TODO: There is probably a better way to do this...
        AMOUNT = 5
        colour = '#006400' if status else 'red'
        pre = '<big>' * AMOUNT
        post = '</big>' * AMOUNT
        return ''.join(['<span color="%s">' % colour,
                        pre, text, post, '</span>'])

    def _subsystem(self, subsystem, widget):
        '''
        Helper function to manage the self.active_systems record
        '''
        if widget.get_active():
            self.active_systems.add(subsystem)
        else:
            self.active_systems.remove(subsystem)

    def _set_button_sensitivity(self, status):
        '''
        Allow to change sensitivity of all buttons on screen.
        '''
        for button in self.all_buttons:
            button.set_sensitive(status)

    def on_run_button_toggled(self, widget):
        self.run_mode = widget.get_active()
        if self.run_mode:
            log.debug('Run button is ON')
            self.freerunner.gps_status = True
            bbox.open_tracking_session()
        else:
            log.debug('Run button is OFF')
            self.freerunner.gps_status = False
            bbox.close_tracking_session()

    def on_window_destroy(self, widget):  #@UnusedVariable
        '''
        Works as far as you follow conventions...
        '''
        log.debug('Program terminated regularly')
        gtk.main_quit()


class LockScreen(graphics.Scene):

    '''
    iPhone-like lock screen widget for the FreeRunner.
    '''

    def __init__(self, callback):
        self.callback = callback
        self.notch_h = 50
        graphics.Scene.__init__(self)
        self.hint = graphics.Label(LS_TEXT[True], self.notch_h / 2,
                               "#000", x=2.5*LS_NOTCH_W, y=self.notch_h*0.75)
        self.add_child(self.hint)
        self.notch = Notch(LS_NOTCH_W, self.notch_h)
        self.add_child(self.notch)
        self.connect("on-enter-frame", self.on_enter_frame)
        self.connect("on-drag-finish", self.on_drag_finish)

    def on_enter_frame(self, scene, context):  #@UnusedVariable
        self.notch.y = self.notch_h
        self.notch.x = self.notch.x if self.notch.x > LS_NOTCH_W \
                                    else LS_NOTCH_W
        self.notch.x = self.notch.x if self.notch.x < self.width - LS_NOTCH_W \
                                    else self.width - LS_NOTCH_W

    def on_drag_finish(self, scene, sprite, event):  #@UnusedVariable
        if self.notch.x >= self.width - LS_NOTCH_W:
            self.notch.unlocked = not self.notch.unlocked
            self.notch.render()
            self.callback(self.notch.unlocked)
            self.hint.text = (LS_TEXT[self.notch.unlocked])
        self.animate(self.notch, x = LS_NOTCH_W,
                     easing = tween.Easing.Quart.ease_out)


class Notch(graphics.Sprite):

    '''
    Sprite for the LockScreen.
    '''

    def __init__(self, x, y):
        self.notch_h = y
        graphics.Sprite.__init__(self, x, y)
        self.unlocked = True
        self.draggable = True   # allow dragging
        self.render()

    def render(self):
        self.graphics.rectangle(-LS_NOTCH_W, -self.notch_h,
                                LS_NOTCH_W*2, self.notch_h*2, 5)
        self.graphics.fill(LS_COLORS[self.unlocked])


