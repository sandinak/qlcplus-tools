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
import sys
from os import path
from urllib.parse import urlparse
from html.parser import HTMLParser
from QLC import QLC

SENDOSC = '/usr/local/bin/sendosc'

# TODO: 
EXPORTED_FUNCTIONS = [
    'audioOff',
    'audioOn',
    'fullscreenOff',
    'fullscreenOn',
    'goto10',
    'goto20',
    'goto30',
    'jump',
    'loopOn',
    'loopOff',
    'panic',
    'pause',
    'play',
    'rewind',
    'toggleFullscreen',
    'toggleLoop',
    'togglePlay',
    'toggleTransitionOnPlay',
    'transitiionOnPlayOff',
    'transitiionOnPlayOn',
]

# default looking at localhost. 
URL='http://127.0.0.1:51000'

DESC = '''
This tool will:
- ingest a showfile
- connect to a Mitti OSC server
- expand each Mitti Cues into a callable 'script' scene
- edit in place or (over) write a new file
'''

def _match(list, item):
    for i in list:
        if item == i:
            return item
    return None


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
        self.functions = []
        self.last_cf = ''
        self.text = {}
        self.reset()

        # parse the data
        self.feed(data)
        return self.functions, self.cues, self.text

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
            # NOTE: leading / means idx 0 is None
            pdata = data.split('/')

            # handle per-cue functions
            if len(pdata) >= 4:
                cue_id = pdata[2]
                function = pdata[3]
                self.last_cf = '%s/%s' % (cue_id,function)
                if not self.cues.get(cue_id):
                    self.cues[cue_id] = []
                self.cues[cue_id].append(function)

            # handle global functions
            elif len(pdata) == 3:
                function = pdata[2] 
                self.last_cf = '%s' % (function)
                self.functions.append(function)
        else:
            if self.last_cf not in self.text:
                info = data.split('.')[0]
                self.text[self.last_cf] = info

def sync_mitti(args, q, url):
    
    # break out URL
    u = urlparse(args.url)

    # Grab current OSC config
    try: 
        with urllib.request.urlopen(args.url) as response:
            html = response.read().decode('utf-8')
    except Exception as e:
        print('unable to connect to %s: %s' % ( url, str(e)))
        sys.exit(1)

    if not html: 
        print('no data from %s:' % url )
        sys.exit(1)
    osc = OSC_HTMLParser()
    g_functions, cues, text = osc.read(html)

    # create scripts for all functions.
    # NOTE: these are all using NAME as significant as we can't predict ID
    # NOTE: have asked Mitti Developer to add name to the OSC server. 
    # build the command
    syscmd = [ 
        'systemcommand:%s' % args.sendosc,
        'arg:%s' % u.hostname,
        'arg:%d' % u.port or 51000 ]
    cmd = ' '.join( syscmd )

    # create the script scenes
    for cue, functions in cues.items():
        for function in functions: 
            this_cmd = cmd
            cf = '%s/%s' % (cue, function)
            if _match(EXPORTED_FUNCTIONS, function):
                if cf in text:
                    this_cmd = '//Mitti command: %s %s\n' % (cf, text.get(cf)) + cmd
                q.function(
                    Type    = 'Script',
                    Path    = '/Mitti/%s' % cue,
                    Name    = '/Mitti/%s' % cf,
                    Command = this_cmd + ' arg:/mitti/%s/%s' % (cue, function) 
                )

    for function in g_functions: 
        if _match(EXPORTED_FUNCTIONS, function):
            this_cmd = cmd 
            if function in text:
                this_cmd = '//Mitti command: %s %s\n' % (function, text.get(function)) + cmd
            q.function(
                Type    = 'Script',
                Path    = '/Mitti',
                Name    = '/Mitti/%s' % (function),
                Command = this_cmd + ' arg:/mitti/%s' % function
            )


def get_args():
    ''' read arguments from C/L '''
    parser = argparse.ArgumentParser(
        description=DESC,
        formatter_class=argparse.RawTextHelpFormatter)
    parser.set_defaults(help=False)
    parser.set_defaults(overwrite=False)
    parser.set_defaults(inplace=False)
    parser.set_defaults(dump=False)
    parser.add_argument("-i", "--inplace",
                        help='Overwrite the showfile in place.',
                        action="store_true")
    parser.add_argument("-d", "--dump",
                        help='Dump modifications to STDOUT',
                        action="store_true")
    parser.add_argument("-o", "--outputfile",
                        type=str, default=None,
                        help="Write to output file")
    parser.add_argument("-s", "--sendosc",
                        type=str, default=SENDOSC,
                        help="Path to the sendosc executable.")
    parser.add_argument("-u", "--url",
                        type=str, default=URL,
                        help="URL for the Mitti OSC Service")
    parser.add_argument("-F", "--overwrite", action="store_true",
                        help="overwrite existing output file")
    parser.add_argument('showfile', type=str,
                        help='Showfile to extend')

    args = parser.parse_args()
    if args.help or not args.showfile:
        parser.print_help()
        sys.exit(0)

    return args

def main():
     # load a showfile
    args = get_args()

    if not args.outputfile and not args.inplace:
        print('ERR: must specify -i or an outputfile.')
        sys.exit(1)

    if not path.exists(args.sendosc):
        print('WARN: sendosc not found at %s\n  please install from: https://github.com/yoggy/sendosc or brew ')

    # load a showfile
    q = QLC(file='../showfiles/blank.qxw')
    sync_mitti(args, q, URL)

    # handle output
    if args.dump:
        q.workspace.dump()

    elif args.inplace: 
        # this assumes overwrite
        q.workspace.write(args.showfile)

    elif args.outputfile:
        if path.exists(args.outputfile):
            if not args.overwrite:
                yn = input(f'Overwrite {args.outputfile} [yN] ?')
                if 'y' in yn.lower():
                    q.workspace.write(args.outputfle)
            else:
                    q.workspace.write(args.outputfle)

if __name__ == '__main__':
    main()

