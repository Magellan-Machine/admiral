#!/usr/bin/env python
# -*- coding: utf-8  -*-
'''
Main module for the FreeRunner logging utility.
'''

import logging

import gtk #@UnresolvedImport

from gui import FreeRunnerControlPanel

__author__ = "Mac Ryan"
__copyright__ = "Copyright ©2011, Mac Ryan"
#__credits__ = ["Name Lastname", "Name Lastname"]
__license__ = "GPL v3"
#__version__ = "<dev>"
#__date__ = "<unknown>"
__maintainer__ = "Mac Ryan"
__email__ = "quasipedia@gmail.com"
__status__ = "Development"


def init_general_log():
    '''
    Initiliase the general logger (and returns it for convenience).
    '''
    logger = logging.getLogger('general')
    logger.setLevel(logging.INFO)  #INFO, WARNING, ERROR, CRITICAL
    handler = logging.FileHandler('../logs/general.log')
    fmt = '%(asctime)s  %(levelname)9s  %(message)s'
    formatter = logging.Formatter(fmt=fmt)
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger

def main():
    log = init_general_log()
    log.info('########################### NEW PROGRAM RUN ######')
    FreeRunnerControlPanel()
    gtk.main()

if __name__ == '__main__':
    main()
