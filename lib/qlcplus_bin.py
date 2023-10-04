#! /usr/bin/env python

'''
============================================================================
Title: discover qlc version
Description:
create fixtures from basic config
============================================================================
'''

import platform
import os

BINPATH = {
    'Darwin': '/Applications/QLC+.app/Contents/MacOS/qlcplus',
    }

class qlc_bin:
    def __init__(self, **kwargs)

        ''' setup class '''
        self.__dict__.update(kwargs)
        system = platform.system()
        
        _bin = self._find_bin()
        help = os.system(_bin + ' --help')
        
        version = self._parse_help(help)

        
        def _find_bin(self):
            if 
        
        