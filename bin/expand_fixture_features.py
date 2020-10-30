#! /usr/bin/env python3

'''
============================================================================
Title: expand_fixture_features
Description:
Tool to pull osc config from Mitti and push script entries for QLC+
============================================================================
'''
# -*- coding: utf-8 -*-

import argparse
import sys
from os import path

from QLC import QLC

DESC = '''
This tool will:
- ingest a showfile
- ingest known fixtures based on normal QLC pathing
- expand fixture capabilities by fixture group into scenes
- edit in place or (over) write a new file
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
    parser.add_argument("-o", "--outputfile",
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

    #  load the file and expand
    q = QLC(args.showfile)
    q.expand_fixture_group_capabilities()

    # handle output
    if args.dump:
        q.workspace.dump()

    elif not args.outputfile: 
        if not args.inplace: 
            yn = input(f'Overwrite {args.shofile} [yN] ?')
            if not 'y' in yn: 
                sys.exit(0)

        q.workspace.write(args.showfile)

    else:
        if path.exists(args.outputfile):
            if not args.overwrite:
                yn = input(f'Overwrite {args.outputfile} [yN] ?')
                if 'y' in yn.lower():
                    q.workspace.write(args.outputfle)
            else:
                    q.workspace.write(args.outputfle)


if __name__ == '__main__':
    main()
