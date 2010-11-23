#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Program to monitor and remotely control CircumSail, the autonomous sailing
robot. The program uses serial communication to interact with the onboard
Arduino.
'''

__author__ = "Mac Ryan (mac@magellanmachine.se)"
__created__ = "2010/09/09"
__copyright__ = "Copyright (c) 2010 The Magellan Machinep"
__license__ = "GPLv3 - http://www.gnu.org/licenses/gpl.html"


import gtk
import platform
from gui import ComputerControlPanel, FreeRunnerControlPanel

# -----------------------------------------------------------------------------
# --- MAIN PROGRAM
# -----------------------------------------------------------------------------

if __name__ == '__main__':

    if platform.machine() == "armv4tl":     # Freerunner
        host = "freerunner"
        interface = FreeRunnerControlPanel
    else:
        host = "computer"
        interface = ComputerControlPanel
    interface()
    gtk.main()
