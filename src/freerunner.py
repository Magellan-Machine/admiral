# -*- coding: utf-8 -*-
'''
Class for easy-interaction with the freerunner.
'''

import os
import dbus
import platform

__author__ = "Mac Ryan"
__copyright__ = "Copyright ©2011, Mac Ryan"
#__credits__ = ["Name Lastname", "Name Lastname"]
__license__ = "GPL v3"
#__version__ = "<dev>"
#__date__ = "<unknown>"
__maintainer__ = "Mac Ryan"
__email__ = "quasipedia@gmail.com"
__status__ = "Development"


class EnvironmentIsNotFreeRunnerError(RuntimeError):

    pass


class FreeRunner(object):

    '''
    Provide transparent access to FreeRunner properties.

    The entire idea of the class is to be able to read or write data with
    the standard Python syntax (i.e.: "freerunner.gps" should return GPS
    coordinates, while "freerunner.wifi = OFF" should switch the wireless off)
    '''

    # Throw exception if software is not running on FreeRunner
    if platform.machine() != "armv4tl":
        msg = 'This software must run on the OpenMoko FreeRunner!'
        raise EnvironmentIsNotFreeRunnerError(msg)
    GET = 0
    SET = 1
    __bus = dbus.SystemBus()
    __dbus_usage = dbus.Interface(__bus.get_object(
        'org.freesmartphone.ousaged', '/org/freesmartphone/Usage'),
        'org.freesmartphone.Usage')
    __dbus_gpsposition = dbus.Interface(__bus.get_object(
        'org.freesmartphone.ogpsd', '/org/freedesktop/Gypsy'),
        'org.freedesktop.Gypsy.Position')
    __dbus_gpsaccuracy = dbus.Interface(__bus.get_object(
        'org.freesmartphone.ogpsd', '/org/freedesktop/Gypsy'),
        'org.freedesktop.Gypsy.Accuracy')
    __dbus_gpscourse = dbus.Interface(__bus.get_object(
        'org.freesmartphone.ogpsd', '/org/freedesktop/Gypsy'),
        'org.freedesktop.Gypsy.Course')
    __property_files = dict(
        usb_mode='/sys/devices/platform/s3c-ohci/usb_mode',
        power_mode='/sys/class/i2c-adapter/i2c-0/0-0073/'
                   'neo1973-pm-host.0/hostmode',
        gps_mode='/sys/class/i2c-adapter/i2c-0/0-0073/'
                 'pcf50633-regltr.7/neo1973-pm-gps.0/power_on')

    @property
    def usb_mode(self):
        '''
        Host or Device?
        '''
        return self._handle_property_on_file(
               self.GET, self.__property_files['usb_mode'])

    @usb_mode.setter
    def usb_mode(self, value):
        '''
        Possible values:
        - 'device'
        - 'host'
        '''
        assert value in ('device', 'host')
        self._handle_property_on_file(
                self.SET, self.__property_files['usb_mode'], value)

    @property
    def power_mode(self):
        '''
        Giving or taking energy from USB port?
        '''
        return self._handle_property_on_file(
                 self.GET, self.__property_files['power_mode'])

    @power_mode.setter
    def power_mode(self, value):
        '''
        Possible values:
        - 0: (TAKING energy via USB)
        - 1: (GIVING energy to USB)
        '''
        assert value in (0, 1)
        self._handle_property_on_file(
                self.SET, self.__property_files['power_mode'], value)

    @property
    def gps_status(self):
        '''
        ON or OFF?
        '''
        r = self._handle_property_on_file(
                  self.GET, self.__property_files['gps_mode'])
        assert r in ('0', '1')
        return True if r == '1' else False

    @gps_status.setter
    def gps_status(self, value):
        '''
        Possible values:
        - True
        - False
        '''
        assert value in (True, False)
        if value == True:
            self.__dbus_usage.RequestResource("GPS")
        else:
            if self.gps_status:
                self.__dbus_usage.ReleaseResource("GPS")

    @property
    def gps_fix(self):
        '''
        Return the GPS current fix
        '''
        if not self.gps_status:
            return None
        pos_data = self.__dbus_gpsposition.GetPosition()
        (bitmask, epoch, lat, lon, alt) = pos_data  #@UnusedVariable
        lat, lon = lat.real, lon.real  #convert from dbus object to floats
        if (lon, lat) == (0, 0):
            return None
        return lat, lon

    @property
    def gps_hdop(self):
        '''
        Return the GPS HDOP (horizontal diluition of precision).
        '''
        if not self.gps_status:
            return None
        accuracy_data = self.__dbus_gpsaccuracy.GetAccuracy()
        (bitmask, pdop, hdop, vdop) = accuracy_data  #@UnusedVariable
        return hdop.real

    @property
    def gps_moving(self):
        '''
        Return heading and speed.
        '''
        if not self.gps_status:
            return None
        course_data = self.__dbus_gpscourse.GetCourse()
        (bitmask, tstamp, speed, heading, climb) = course_data #@UnusedVariable
        return heading.real, speed.real * 0.514444444  #convert kt --> ms

    def _handle_property_on_file(self, mode, file, value=None):
        '''
        Some of the FreeRunner functionalities accept input or output through
        the content of some file. This handler transparently manage querying or
        setting data in such files.
        - ``mode``: set | get
        - ``file``: full path to property file
        - ``value``: value to set (defaults to None when used with mode=get)
        '''
        assert mode in (self.SET, self.GET)
        if mode == self.GET:
            return os.popen("cat " + file).read().strip()
        if mode == self.SET:
            assert value != None
            os.system(' '.join(("echo", str(value), ">", file)))