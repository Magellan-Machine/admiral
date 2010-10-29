# -*- coding: utf-8 -*-
'''
Created on 25 Sep 2010

@author: Mac Ryan

@file: Class for eay-interaction with the freerunner.
'''

import os
import struct
import dbus
import platform
from time import sleep
from operator import mul
from commons import *

# -----------------------------------------------------------------------------
# --- ERROR AND EXCEPTIONS DEFINITIONS
# -----------------------------------------------------------------------------

class ReadOnlyFreeRunnerProprietyError(Exception):
    
    def __init__(self, value):
        self.parameter = value
      
    def __str__(self):
        return repr(self.parameter)

class WriteOnlyFreeRunnerProprietyError(Exception):
    
    def __init__(self, value):
        self.parameter = value
      
    def __str__(self):
        return repr(self.parameter)

class NotFreeRunnerSpecialProprietyError(Exception):
    
    def __init__(self, value):
        self.parameter = value
      
    def __str__(self):
        return repr(self.parameter)

class EnvironmentIsNotFreeRunnerError(Exception):
    
    def __init__(self, value):
        self.parameter = value
      
    def __str__(self):
        return repr(self.parameter)

# -----------------------------------------------------------------------------
# --- MAIN CLASS
# -----------------------------------------------------------------------------

class FreeRunner(object):
    
    '''
    Provide transparent access to FreeRunner proprieties.
    
    The entire idea of the class is to be able to read or write data with
    the standard python syntax (i.e.: "freerunner.gps" should return GPS 
    co-ordinates, while "freerunner.wifi = OFF" should switch the wireless off)
    '''

    # CLASS ATTRIBUTES (bypass __getattr__ and __setattr__)
    # The property_handlers dictionary provides a method and the arguments
    # to properly handle the setting/getting of each property
    if platform.machine() == "armv4tl":
        bus = dbus.SystemBus()
        dbus_wifi = dbus.Interface(bus.get_object("org.freesmartphone.odeviced", 
            "/org/freesmartphone/Device/PowerControl/WiFi"), 
            "org.freesmartphone.Resource")
        dbus_usage = dbus.Interface(bus.get_object("org.freesmartphone.ousaged", 
            "/org/freesmartphone/Usage"), "org.freesmartphone.Usage")
        dbus_gps = dbus.Interface(bus.get_object("org.freesmartphone.ogpsd", 
            "/org/freedesktop/Gypsy"), "org.freedesktop.Gypsy.Position")
        property_handlers = {
            'usb_mode'       : ('_file_handler', "/sys/devices/platform/s3c-ohci/usb_mode"),
            'pwr_mode'       : ('_file_handler', "/sys/class/i2c-adapter/i2c-0/0-0073/neo1973-pm-host.0/hostmode"),
            'gps_mode'       : ('_file_handler', "/sys/class/i2c-adapter/i2c-0/0-0073/pcf50633-regltr.7/neo1973-pm-gps.0/power_on"),
            # http://wiki.openmoko.org/wiki/GTA02_sysfs
            # Current being drawn from battery (+ve) or pushed into battery 
            # during charging (-ve) in uA 
            'bat_absorption' : ('_file_handler', "/sys/class/power_supply/battery/current_now"),
            # At current rate of discharge, estimate of how long we can run for. 
            # If battery is not discharging, it won't make an estimate and will 
            # return a magic value "3932100" meaning "no estimate". The coulomb
            # counter averages the load and adjusts this value slowly to be its 
            # estimate of when we will blow chunks. 
            'bat_timeleft'   : ('_file_handler', "/sys/class/power_supply/battery/time_to_empty_now"),
            'wifi'           : ('_wifi_handler',),
            'accelerometer'  : ('_accel_handler',),
        }
        tmp = os.popen('ls /etc/wpa_supplicant/wpa_supplicant.conf.*').readlines()
        configured_networks = [f.strip()[f.rfind('.')+1:] for f in tmp]
        del tmp
        del bus
        running_on_freerunner = True
    else:
        running_on_freerunner = False

    def __init__(self):
        '''
        Instantiation of an object is forbidden if we are not running on a FR"
        '''
        if self.running_on_freerunner == False:
            raise EnvironmentIsNotFreeRunnerError(
                  "The program is not running on a FreeRunner")

    def __getattr__(self, attribute):
        if attribute not in self.property_handlers.keys():
            raise NotFreeRunnerSpecialProprietyError(attribute)
        else:
            handler = getattr(self, self.property_handlers[attribute][0])
            return handler('get', attribute)
    
    def __setattr__(self, attribute, value):
        if attribute not in self.property_handlers.keys():
            super(FreeRunner, self).__setattr__(attribute, value)
        else:
            if attribute[:4] == 'bat_':
                raise ReadOnlyFreeRunnerProprietyError(attribute, value)
            handler = getattr(self, self.property_handlers[attribute][0])
            handler('set', attribute, value)
    
    def _file_handler(self, mode, attribute, value=None):
        '''
        Write or read from a file.
        '''
        file = self.property_handlers[attribute][1]
        if mode == 'get':
            return os.popen("cat " + file).read().strip()
        if mode == 'set':
            os.system(' '.join(("echo", str(value), ">", file)))
    
    def _wifi_handler(self, mode, attribute, value=None):
        '''
        Map the Enable() and Disable() dbus methods to ON and OFF states.
        '''
        if mode == 'get':
            raise WriteOnlyFreeRunnerProprietyError(attribute, value)
        else:
            if value == OFF:
                self.dbus_wifi.Disable()
            if value == ON:
                self.dbus_wifi.Enable()
    
    def _accel_handler(self, mode, attribute, value=None):
        '''
        Does the whole procedure for reading a single set of x,y,z data.
        
        More on the theory behind the code can be found at:
        http://wiki.openmoko.org/wiki/Accelerometer_data_retrieval
        '''
        if mode == 'set':
            raise ReadOnlyFreeRunnerProprietyError(attribute, value)
        else:
            result = [None]*3
            with open("/dev/input/event3", "rb") as acc:
                acc.read(64) # flushes old data [DO NOT REMOVE!!]
                while True:
                    event = acc.read(16)
                    t1, t2, type, code, value = struct.unpack('iihhi', event)        
                    if type == 2 or type == 3:
                        result[code] = value    # codes for x,y,z are 0,1,2...
                    if type == 0 and code == 0 and None not in result:
                        return result
    
    def connect_to_network(self, network):
        '''
        Reset the wireless interface and try to connect to a given network.
        '''
        print(">>> Overwriting wpa_supplicant.conf... <<<")
        os.system ("cp /etc/wpa_supplicant/wpa_supplicant.conf." + network + " /etc/wpa_supplicant/wpa_supplicant.conf")
        os.system("ifdown eth0")
        print(">>> Bringing down ETH0... <<<")
        sleep(1)
        print(">>> Disabling Wireless... <<<")
        self.wifi = OFF
        sleep(1)      
        print(">>> Re-enabling Wireless... <<<")
        self.wifi = ON
        sleep(1)      
        print(">>> Bringing down ETH0... Yes... AGAIN!! <<<")
        sleep(1)
        print(">>> Bringing up ETH0... Good Luck Sailor! <<<")
        os.system("ifup eth0")
        sleep(1)
        print("+------------------------+")
        print("| NETWORK RESET FINISHED |")
        print("+------------------------+")
    
    def gps_up(self):
        self.gps_mode = 1
        self.dbus_usage.RequestResource("GPS")
        
    def gps_down(self):
        self.dbus_usage.ReleaseResource("GPS")
        self.gps_mode = 0
        
    def get_gps(self):
        (bitmask, epoch, lat, lon, alt) = self.dbus_gps.GetPosition()
        return (lat.real, lon.real)