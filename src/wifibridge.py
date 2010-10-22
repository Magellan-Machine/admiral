'''
Created on 14 Oct 2010

@author: mac
@file: Provide functionality for creating a wireless bridge using sockets
'''

import socket
from commons import *
from time import time

class WifiBridge(object):
    '''
    classdocs
    '''
    def __init__(self):
        
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind(("", WIFI_SERVER_PORT))
        self.socket.setblocking(0)
        self.bond_to = None # Will contain tuple (host, port) of linked remote station
        
    def request_bind(self, target):
        '''
        Send request to link with server.
        '''
        self.write("link-request " + str(WIFI_SERVER_PORT), target)
        start = time()
        while time() < start + WIFI_TIMEOUT:
            answer = self.read()
            if answer != None and answer[0] == "linked":
                self.bond_to = target
                return True
        return False

    def accept_bind(self):
        '''
        Accept binding request if there is one.
        '''
        assert self.bond_to == None
        msg = self.read()
        if msg:
            if msg[0].split()[0] == "link-request":
                self.bond_to = (msg[1][0], int(msg[0].split()[1]))
                print self.bond_to
                self.write("linked")
                return True
        return False

    def read(self):
        '''
        Read messages from the wifi bridge.
        
        Can return:
        - None               : no message present
        - data, (host, port) : if the server is not linked to a client
        - data               : if the server is already linked
        '''
        try:
            res = self.socket.recvfrom(1024)
        except socket.error:
            return None
        print res
        if self.bond_to:
            return res[0]
        else:
            return res
    
    def write(self, data, server=None):
        if server == None:
            server = self.bond_to
        assert server != None
        self.socket.sendto(data, server)
