#! /usr/bin/env python

'''
============================================================================
Title: manage qlc showfile
Description:
create fixtures from basic config
============================================================================
'''

import logging as log
import lxml.etree as ET
from xml.dom import minidom
import copy

colormap = {
    'R': 'Red',
    'G': 'Green',
    'B': 'Blue',
    'W': 'White',
    'P': 'Purple',
    'C': 'Cyan',
    'Y': 'Yellow',
    'U': 'UltraViolet',
}

ENCODING='UTF-8'
XMLNS='http://www.qlcplus.org/FixtureDefinition'
DOCTYPE='<!DOCTYPE FixtureDefinition>'

class qlc:

    def __init__(self, **kwargs):
        ''' setup class '''
        # expand common targets
        self.__dict__.update(kwargs)
        self.colors = self.config.get('colors')
        self._read_file()
        
        self.engine = self.xml.find('Engine')
        self.fixtures = self.xml.find('Fixture')
        self.fixture_groups = self.xml.find('FixtureGroup')
        self.functions = self.xml.find('Function')
        self.rgb_matrixes = self.functions.findall(
            "Function[@Type='RGBMatrix']/Name")

    def _expand_rgb_matrix_per_group(self):

class showfile: 
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)
        self._readfile()
        self._parsefile()

    def _read_file(self):
        self.xml = ET.parse(self.file)
    
    def _parse_file(self):
        self.creator = self.xml.



''' qlc engine '''        
class engine: 
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)
        qlc.__init__(self, **kawargs)
    
class rgb_matrix: 
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)
        engine.__init__(self, **kawargs)
        
        
        
