#! /usr/bin/env python3

'''
============================================================================
Title: generate fixtures based on definitions
Description:
Pulls in config from yaml and generates fixtures and layouts.
============================================================================
'''
# -*- coding: utf-8 -*-

import argparse
import sys
import yaml
import logging
import pprint
import os

from QLC import QLC

logger = logging.getLogger(__name__)

DESC = '''
This tool will:
- ingest a yaml config
- ingest a showfile 
- ingest known fixtures based on normal QLC pathing
- generate/update fixture definitions based on config
- generate/update fixtures based on config
- generate/update fixture groups based on config
- edit in place or (over) write a new showfile 
'''

def setup_logging(args):
    """ setup logging """
    global debug, verbose
    llevel = logging.ERROR
    if args.debug:
        llevel = logging.DEBUG
        print("logging debug")
    elif args.verbose:
        llevel = logging.INFO
        print("logging verbose")

    if args.logfile:
        if not os.access(args.logfile, os.W_OK):
            print("ERROR: Unable to write to %s")
            sys.exit(1)
        logging.basicConfig(filename=args.logfile, level=llevel)
    else:
        logging.basicConfig(level=llevel)

def get_args():
    ''' read arguments from C/L '''
    parser = argparse.ArgumentParser(
        description=DESC,
        formatter_class=argparse.RawTextHelpFormatter)
    parser.set_defaults(help=False)
    parser.set_defaults(overwrite=False)
    parser.set_defaults(inplace=False)
    parser.set_defaults(dump=False)
    parser.set_defaults(verbose=False)
    parser.set_defaults(debug=False)
    parser.add_argument("-V", "--verbose",
                        help='enable verbose output',
                        action="store_true")
    parser.add_argument("-D", "--debug",
                        help='enable debugging output',
                        action="store_true")
    parser.add_argument("--logfile", help="Send output to a file.")
    parser.add_argument("-i", "--inplace",
                        help='Overwrite the showfile in place.',
                        action="store_true")
    parser.add_argument("-d", "--dump",
                        help='Dump modifications to STDOUT',
                        action="store_true")
    parser.add_argument("-c", "--config_file",
                        type=str, default=None,
                        help="config file with definitions")
    parser.add_argument("-o", "--output_file",
                        type=str, default=None,
                        help="Write to output file")
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
    setup_logging(args)

    # load the config 
    with open(args.config_file) as file:
        cfg = yaml.load(file,Loader=yaml.FullLoader)

    #  load the file and expand
    q = QLC(args.showfile)

    universes = cfg.get('universes', [])
    if universes:
        logger.info('generating %d universes' % len(universes))
        q.generate_universes(universes)
    q.workspace.dump()

    fixtures = cfg.get('fixtures', [])
    if fixtures:
        logger.info('generating %d fixtures' % len(fixtures))
        q.generate_fixtures(cfg.get('fixtures'))

    fixture_groups = cfg.get('fixture_groups', [])
    if fixture_groups: 
        logger.info('generating %d fixture_groups' % len(fixture_groups))
        q.generate_fixture_groups(fixture_groups)

    # q.expand_fixture_group_capabilities()

    # handle output
    if args.dump:
        logger.info('dumping workspace')
        q.workspace.dump()

    elif not args.output_file: 
        if not args.inplace: 
            yn = input(f'Overwrite {args.showfile} [yN] ?')
            if not 'y' in yn: 
                sys.exit(0)

        q.workspace.write(args.showfile)

    else:
        if os.path.exists(args.output_file):
            if not args.overwrite:
                yn = input(f'Overwrite {args.output_file} [yN] ?')
                if 'y' in yn.lower():
                    q.workspace.write(args.outputfle)
            else:
                    q.workspace.write(args.outputfle)


if __name__ == '__main__':
    main()
