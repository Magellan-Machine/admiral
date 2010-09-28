#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Created on 9 Sep 2010

@author: Mac Ryan

@file: Program to monitor and remotely control CircumSail, the autonomous sailing
robot. The program uses serial communication to interact with the onboard 
Arduino. 
'''


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
