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
import urllib.request
from urllib.parse import urlparse
from html.parser import HTMLParser

BASE_FUNCTION_ID=10000
EXPORTED_FUNCTIONS = [
    'play',
    'jump',
    'loopOn',
    'loopOff',
]
URL='http://127.0.0.1:51000'

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

def sync_mitti(q, url):
    
    # break out URL
    u = urlparse(url)

    # Grab current OSC config
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
            fid = BASE_FUNCTION_ID + (int(cue) * 100)
            for function in functions: 
                if not function in EXPORTED_FUNCTIONS:
                    continue
                cmd = 'systemcommand:/usr/local/bin/sendosc ' 
                cmd += "arg:%s " % u.hostname
                cmd += "arg:%d " % u.port
                cmd += "arg:/mitti/%s/%s" % (cue, function)
                q.function(
                    Name    = '/Mitti/%s/%s' % (cue, function),
                    Path    = '/Mitti/%s' % (cue),
                    Type    = 'Script',
                    ID      = fid,
                    Command = cmd
                )
                fid += 1

# load a showfile
q = qlc(file='../showfiles/blank.qxw')

# expand color scenes for fixtures
sync_mitti(q, URL)

q.write()
