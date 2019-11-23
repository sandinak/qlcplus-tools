#! /usr/bin/env python

'''
============================================================================
Title: manage qlc showfile
Description:
QLC Libraries
============================================================================
'''

import logging as log
import xml.etree.ElementTree as ET
import copy
import pprint

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
#         self._read_file()
#         
#         self.engine = self.xml.find('Engine')
#         self.fixtures = self.xml.find('Fixture')
#         self.fixture_groups = self.xml.find('FixtureGroup')
#         self.functions = self.xml.find('Function')
#         self.rgb_matrixes = self.functions.findall(
#             "Function[@Type='RGBMatrix']/Name")

class showfile(qlc): 

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)
        self._readfile()
        self._parsefile()

    def _readfile(self):
        self.tree = ET.parse(self.file)
        self.root = self.tree.getroot()
    
    def _parsefile(self):
        for elem in self.root:
            tag = elem.tag
            if 'Creator' in tag: 
                self.Creator = self._parse_engine(tag)
            elif 'Engine' in tag:
                self.engine = self._parse_engine(tag)



''' qlc engine '''        
class engine: 
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)
        qlc.__init__(self, **kwargs)
    
class rgb_matrix: 
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)
        engine.__init__(self, **kawargs)
        
        
        
