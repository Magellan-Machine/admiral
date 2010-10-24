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
    def __init__(self, remote_address=None):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind(("", WIFI_PORT))
        self.socket.setblocking(0)
        self.remote_address = remote_address
        self.last_ping_request_time = 0

    def read(self):
        '''
        Read messages from the wifi bridge.
        
        Can return:
        - None               : no message present
        - data, (host, port) : if the server is not linked to a client
        - data               : if the server is already linked
        '''
        try:
            if self.remote_address:
                msg = self.socket.recv(1024)
            else:
                msg, self.remote_address = self.socket.recvfrom(1024)
                self.last_wifi_in_time = time()  # first msg ever received
        except socket.error:
            return None
        else:
            self.last_wifi_in_time = time()
            if msg == 'ping':
                self.write('pong')
                return None
            if msg == 'pong':
                return None
            else:
                return msg    
    
    def write(self, data, server=None):
        if server == None:
            server = self.remote_address
        assert server != None
        self.socket.sendto(data, server)

    def ping(self):
        if time() - self.last_ping_request_time > 0.5: # prevent flooding
            self.write('ping')
            self.last_ping_request_time = time()