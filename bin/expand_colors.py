#! /usr/bin/env python3

'''
============================================================================
Title: sync_osc
Description:
Tool to pull osc config from Mitti and push script entries for QLC+
============================================================================
'''
# -*- coding: utf-8 -*-

import argparse

import argparse
import logging as log
import os
import pprint
import sys
import time
import urllib.request
from html.parser import HTMLParser

BASE_FUNCTION_ID=10000
EXPORTED_FUNCTIONS = [
    'play',
    'jump',
    'loopOn',
    'loopOff',
]

import yaml

from qlc import qlc

class OSC_HTMLParser(HTMLParser):
    ''' We rip all the <strong> headings out as those are the valid
        commands. 
        NOTE: interestingly cue's start at 1 not zero .. so to keep things
        consistent .. I am using a dict of lists '''
    def __init__(self):
        HTMLParser.__init__(self)

    def read(self, data):
        ''' read the input and return a list of cues '''
        # clear output and reset parsers state
        self.cues = {}
        self.reset()

        # parse the data
        self.feed(data)
        return self.cues

    def handle_starttag(self, tag, attrs):
        ''' all the cue's are in <strong> Tags '''
        if tag == 'strong':
            self.valid_data = 1
    
    def handle_endtag(self, tag):
        self.valid_data = 0

    def handle_data(self, data):
        ''' split the cues' out .. eventually we will want 
            to merge this with config so we can default some
            of the actions that take values, right now we only
            operate on functions that require no value '''
        if self.valid_data:
            # this is weird because some functions have subconfig 
            pdata = data.split('/')
            if len(pdata) >= 4:
                cue_id = pdata[2]
                function = pdata[3]
                if not self.cues.get(cue_id):
                    self.cues[cue_id] = []
                self.cues[cue_id].append(function)

def sync_mitti():
    # sync mitti
    with urllib.request.urlopen('http://localhost:51000') as response:
        html = response.read().decode('utf-8')
    if html: 
        osc = OSC_HTMLParser()
        cues = osc.read(html)

        host_args = [
            'arg:127.0.0.1',
            'arg:51000',
        ]

        # create scripts for all functions.
        for cue,functions in cues.items():
            for function in functions: 
                if not function in EXPORTED_FUNCTIONS:
                    continue
                name = '/Mitti/%s/%s' % (cue, function)
                q.function(
                    Name    = name,
                    Path    = name,
                    Type    = 'Script',
                    ID      = (BASE_FUNCTION_ID + int(cue)),
                    Command = 'systemcommand:/usr/local/bin/sendosc ' 
                                "arg: 127.0.0.1 arg:51000 " 
                                "arg:/mitti/%s/%s" % (cue, function)
                )

# load a showfile
q = qlc(file='../showfiles/blank.qxw')

# expand color scenes for fixtures
q.expand_fixture_group_capabilities()

q.write()
