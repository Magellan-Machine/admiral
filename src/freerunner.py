#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Created on 25 Sep 2010

@author: mac
'''

import os

class NotKnownFreeRunnerProprietyError(Exception):
    
    def __init__(self, value):
        self.parameter = value
      
    def __str__(self):
        return repr(self.parameter)

class FreeRunner(object):
    
    '''
    Provide transparent access to FreeRunner proprieties.
    '''
    
    # Class attributes, so they escape the __getattr___ and __setattr__ logic
    attributes = {
        "usb_mode" : "/sys/devices/platform/s3c-ohci/usb_mode",
        "pwr_mode" : "/sys/class/i2c-adapter/i2c-0/0-0073/neo1973-pm-host.0/hostmode",
    }
    
    def __getattr__(self, name):
        try:
            return os.popen("cat " + self.attributes[name]).read()
        except:
            raise NotKnownFreeRunnerProprietyError(name)
        
    def __setattr__(self, name, value):
        try:
            resource = self.attributes[name]
        except:
            raise NotKnownFreeRunnerProprietyError(name)
        os.system(' '.join(("echo", str(value), ">", resource)))
        
    def git_pull(self):
        os.system("git pull git://192.168.1.34/python/CircumSail master")
        
    def eth0_cycle(self):
        os.system("ifdown eth0")
        os.system("ifup eth0")