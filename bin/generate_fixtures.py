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
from os import path

from QLC import QLC

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

    # load the config 
    with open(args.config_file) as file:
        cfg = yaml.load(file,Loader=yaml.FullLoader)

    #  load the file and expand
    q = QLC(args.showfile)

    if 'universes' in cfg:
        q.generate_universes(cfg.get('universes'))
    # generate fixutres if configured .. this is authoritative.
    if 'fixtures' in cfg:
        q.generate_fixtures(cfg.get('fixtures'))


    for fg in cfg.get('fixture_groups'):
        q.generate_fixture_group(fg)
    q.generate_fixtures()
    q.expand_fixture_group_capabilities()

    # handle output
    if args.dump:
        q.workspace.dump()

    elif not args.output_file: 
        if not args.inplace: 
            yn = input(f'Overwrite {args.shofile} [yN] ?')
            if not 'y' in yn: 
                sys.exit(0)

        q.workspace.write(args.showfile)

    else:
        if path.exists(args.output_file):
            if not args.overwrite:
                yn = input(f'Overwrite {args.output_file} [yN] ?')
                if 'y' in yn.lower():
                    q.workspace.write(args.outputfle)
            else:
                    q.workspace.write(args.outputfle)


if __name__ == '__main__':
    main()
