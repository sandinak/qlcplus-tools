#! /usr/bin/env python

'''
============================================================================
Title: manage qlc fixtures
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
    'W': 'White'
}

def_to_fixture = [
    'Manufacturer',
    'Model',
    'Type'
]

physical_order = [
    'Bulb',
    'Dimensions',
    'Technical',
    'Lens',
    'Focus',
    'Layout',
    'Technical']

ENCODING='UTF-8'
XMLNS='http://www.qlcplus.org/FixtureDefinition'
DOCTYPE='<!DOCTYPE FixtureDefinition>'

def _gen_filename(fixture):
    ''' generate filename in QLC format '''
    manufacturer = fixture.get('Manufacturer').replace(' ', '_')
    model = fixture.get('Model').replace(' ', '_')
    return ('%s-%s' % (manufacturer, model))


def _channel_name(head, color):
    ''' create channel name '''
    colorname = colormap[color]
    return '%d-%s' % (head, colorname)


class qlc_fixture:

    def __init__(self, **kwargs):
        ''' setup class '''
        self.__dict__.update(kwargs)
        # process definition
        self._merge_defaults()
        self._set_default_modes()

        # create fixture XML
        self.xml = ET.Element('FixtureDefinition', xmlns=XMLNS)
        self._gen_fixture()

        # create output
        self.text = ET.tostring(
            self.xml, 
            pretty_print=True,
            xml_declaration=True,
            encoding=ENCODING,
            doctype=DOCTYPE)
 
        #self.text = minidom.parseString(self.xml_str).toprettyxml(
        #    indent = ' ' ).encode(ENCODING)
            

    def _set_default_modes(self):
        if 'Modes' not in self.fdef:
            self.fdef['Modes'] = []
        if 'ALL' not in self.fdef.get('Modes'):
            self.fdef['Modes'].append('ALL')

    def _gen_fixture(self):
        ''' create default set for this fixture '''
        self._gen_creator()
        self._gen_fabricator()
        self._gen_by_type()
        self._gen_physical()

    def _gen_creator(self):
        ''' create creator header '''
        creator = ET.SubElement(self.xml, 'Creator')
        for key,val in self.fdef.get('Creator').iteritems():
            item = ET.SubElement(creator, key)
            item.text = str(val)


    def _gen_fabricator(self):
        ''' add fabrication information '''
        manufacturer = ET.SubElement(self.xml, 'Manufacturer')
        manufacturer.text = self.fdef.get('Manufacturer')
        model = ET.SubElement(self.xml, 'Model')
        model.text = self.fdef.get('Model')
        type = ET.SubElement(self.xml, 'Type')
        type.text = self.fdef.get('Type')

    def _gen_physical(self):
        ''' generate physical attributes '''
        physical = ET.SubElement(self.xml, 'Physical')
        for key in physical_order:
            item = ET.SubElement(physical, key)
            for dkey, dval in self.fdef['Physical'].get(key).iteritems():
                item.set(dkey, str(dval))

    def _gen_by_type(self):
        ''' generate channels and modes by type '''
        if 'LED Bar' in self.fdef['Type']:
            self._gen_led_bar()

    # todo: abstract led bar class
    def _gen_led_bar(self):
        ''' Generate LED Bar type from definition '''
        colors = self.fdef.get('Colors')
        heads = int(self.fdef.get('Heads'))
        self._gen_channels(heads, colors)
        self._gen_modes(heads, colors)

    def _gen_channels(self, heads, colors):
        ''' generate channels '''
        for head in range(1, heads+1):
            for color in colors:
                channel = ET.SubElement(self.xml, 'Channel')
                channel.set('Name', _channel_name(head, color))
                colorname = colormap[color]
                channel.set('Preset', 'Intensity%s' % colorname)

    def _gen_modes(self, heads, colors):
        ''' generate modes
            NOTE: channels start at 0 '''
        for mode in self.fdef.get('Modes'):
            if 'ALL' in mode:
                self._gen_mode_all(heads, colors)

    def _gen_mode_all(self, heads, colors):
        ''' all heads and all colors '''
        mode = ET.SubElement(self.xml, 'Mode')
        mode.set('Name', 'ALL')
        # create channels
        i = 0
        for head_id in range(1, heads+1):
            for color in colors:
                channel = ET.SubElement(mode, 'Channel')
                channel.set('Number', str(i))
                channel.text = _channel_name(head_id, color)
                i = i + 1
        # create heads
        i = 0
        for head_id in range(1, heads+1):
            head = ET.SubElement(mode, 'Head')
            for color in colors:
                channel = ET.SubElement(head, 'Channel')
                channel.text = str(i)
                i = i + 1

    def _merge_defaults(self):
        ''' merge defaults '''
        for k, v in self.config.get('default').iteritems():
            if k not in self.fdef:
                self.fdef[k] = copy.deepcopy(v) 
