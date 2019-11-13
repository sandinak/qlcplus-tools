#! /usr/bin/env python

'''
============================================================================
Title: merge yaml to QLC xml 
Description:
 - read config
 - read in workspace file
 - extend matrixes that exist
============================================================================
'''
# -*- coding: utf-8 -*-

from __future__ import print_function

import argparse
import logging as log
import os
import pprint
import sys
import time

import yaml
from qlc import rgb_matrix

# add the calling dir as a library dir so we
# don't have to be in it to run
sys.path.append(os.path.dirname(os.path.abspath(__file__)))


DESC = '''
This tool:
  - reads showfile
  - reads yaml 
  - updates showfile with config
'''

# where the config is
CF_FILE = './showfile.yml'


def get_args():
    ''' read arguments from C/L '''
    parser = argparse.ArgumentParser(
        description=DESC,
        formatter_class=argparse.RawTextHelpFormatter)
    parser.set_defaults(debug=False)
    parser.set_defaults(verbose=False)
    parser.set_defaults(help=False)
    parser.set_defaults(overwrite=False)
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="Set verbose output.")
    parser.add_argument("-d", "--debug", action="store_true",
                        help="Show debugging output.")
    parser.add_argument("-l", "--log", type=str,
                        help="log to file")
    parser.add_argument("-cf", "--config-file", 
                        type=str, default=CF_FILE,
                        help="config file with definitions")
    parser.add_argument('showfile', metavar='S', 
                        type=str, nargs='?',
                        help='Showfile to extend.')
    parser.add_argument("-f", "--force", action="store_true",
                        help="overwrite existing showfile instead of creating.")

    args = parser.parse_args()
    if args.help:
        parser.print_help()
        sys.exit(0)

    if not (os.path.isfile(args.config_file) and
            os.access(args.config_file, os.R_OK)):
        print('config file %s is not readable.' %
              args.config_file)
        sys.exit(1)

    return args


def setup_logging(args):
    ''' setup logging, stdout if no file set '''
    loglevel = log.INFO
    if args.debug:
        loglevel = log.DEBUG

    if args.log:
        # log to a file, default debug
        log.basicConfig(filename=args.log,
                        filemode='a',
                        format=(
                            '%(asctime)s,%(msecs)d '
                            '%(name)s %(levelname)s '
                            '%(message)s'),
                        
                        datefmt='%H:%M:%S',
                        level=loglevel)
    elif args.debug or args.verbose:
        # log to screen
        log.basicConfig(format="%(levelname)s: %(message)s",
                        level=loglevel)
    else:
        # don't log
        log.basicConfig(format="%(levelname)s: %(message)s")

    log.debug("==== Starting %s =====", sys.argv[0])


def read_config(cf_file):
    ''' read the config file and return a dict '''
    log.debug('reading config from %s', cf_file)
    with open(cf_file, "r") as cf_yaml:
        config = yaml.load(cf_yaml, Loader=yaml.FullLoader)
    log.debug(pprint.pformat(config))
    return config


def main():
    ''' main program '''

    # handle args
    args = get_args()
    setup_logging(args)

    config = read_config(args.config_file)
    
    
    

if __name__ == '__main__':
    main()
