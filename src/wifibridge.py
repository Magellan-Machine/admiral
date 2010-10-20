'''
Created on 14 Oct 2010

@author: mac
@file: Provide functionality for creating a wireless bridge using sockets
'''

import socket

class WifiBridge(object):
    '''
    classdocs
    '''
    def __init__(self):
        '''
        Constructor
        '''
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.server_socket.bind(("", 5000))
        self.server_socket.setblocking(0)

    def read(self):
        try:
            res = self.server_socket.recvfrom(1024)
        except socket.error:
            return None
        return res
    
    def write(self, data, host, port):    
        self.client_socket.sendto(data, (host, port))
