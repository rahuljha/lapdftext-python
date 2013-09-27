#!/usr/bin/python

class Error(Exception):
    pass

class FileNotFoundError(Error):
    def __init__(self, msg):
        self.msg = msg
    
