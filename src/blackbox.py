#!/usr/bin/env python
# -*- coding: utf-8  -*-
'''
The blackbox module allows the FreeRunner to perform a function similar to
that provided by flight data and flight voice recorders on commercial
airliners.
'''

import logging
from time import strftime

__author__ = "Mac Ryan"
__copyright__ = "Copyright 2011, Mac Ryan"
__license__ = "GPL v3"
#__version__ = "<dev>"
#__date__ = "<unknown>"
__maintainer__ = "Mac Ryan"
__email__ = "quasipedia@gmail.com"
__status__ = "Development"
__all__ = "blackbox"


log = logging.getLogger('general')
log.debug('BlackBox module initialised.')

class BlackBox(object):

    '''
    The blackbox class transparently manage sailing sessions (logging them to
    different files) reusing the same logger instance, but dinamically creating
    the appropriate file handlers.

    The normal way to log an event in the blackbox is by issuing:
    blackbox.log(<Data-to-be-logged-here>)
    '''

    def __init__(self):
        self.logger = logging.getLogger('blackbox')
        self.logger.setLevel(logging.DEBUG)
        self.active = False  #False or (tracker_id, handler_object)
        self.lines = 0

    def open_tracking_session(self):
        '''
        The new session creates a new file handler, with the name of the file
        equal to the creation date and time. It also automatically close any
        other current sessions if present.
        '''
        if self.active:
            self.close_tracking_session()
        id_ = strftime('%Y-%m-%d@%Hh%M')
        handler = logging.FileHandler(''.join(['../logs/', id_, '.log']))
        fmt = '%(relativeCreated)09d,%(message)s'
        handler.setFormatter(logging.Formatter(fmt=fmt))
        self.logger.addHandler(handler)
        self.active = id_, handler
        self.lines = 0
        log.info('New tracking session started. ID: %s' % id_)

    def close_tracking_session(self, id_=None):
        '''
        Close the ``id_`` tracking session (by deleting its logger handler).
        Return True on success, False otherwise. If ``id_`` is omitted, it
        stops the current tracking session (there can only be a tracking
        session open at time).
        '''
        # Early return if there is no session open
        if not self.active:
            return False
        active_id, active_handler = self.active
        if id_ and id_ != active_id:
            return False
        self.logger.removeHandler(active_handler)
        log.info('Closed tracking session. ID: %s' % active_id)
        self.active = False
        self.lines = 0
        return True

    def log(self, msg):
        '''
        Log a message to the blackbox.
        '''
        self.logger.info(msg)
        self.lines += 1

blackbox = BlackBox()
