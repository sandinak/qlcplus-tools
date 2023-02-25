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
import logging


logger = logging.getLogger(__name__)

from QLC import QLC

DESC = '''
This tool will:
- ingest a showfile
- ingest known fixtures based on normal QLC pathing
- expand fixture capabilities by fixture group into scenes
- edit in place or (over) write a new file
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
    parser.set_defaults(import_fixture_groups=False)
    parser.set_defaults(export_fixture_groups=False)
    parser.set_defaults(expand_fixtures=False)
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
    parser.add_argument("-d", "--dump",
                        help='Dump modifications to STDOUT',
                        action="store_true")

    xls = parser.add_argument_group("XLS Import/Export")
    xls.add_argument("--import-fixture-groups", "-I", help="Import Fixture Groups from XLSX file", action='store_true')
    xls.add_argument("--export-fixture-groups", "-E", help="Export Fixture Groups to XLSX file", action='store_true')
    xls.add_argument("--xls-file", "-x", help="Export Fixture Groups to XLSX file")

    fmgmt = parser.add_argument_group("File IN/Out")
    fmgmt.add_argument("-o", "--outputfile",
                        type=str, default=None,
                        help="Write to output file")
    fmgmt.add_argument("-F", "--overwrite", action="store_true",
                        help="overwrite existing output file")
    fmgmt.add_argument("-i", "--inplace",
                        help='Overwrite the showfile in place.',
                        action="store_true")
    parser.add_argument("-X", "--expand-fixtures", help="Expand Fixture Features into Scenes", action='store_true')

    parser.add_argument('showfile', type=str,
                        help='Showfile to extend')

    args = parser.parse_args()
    if args.help or not args.showfile:
        parser.print_help()
        sys.exit(0)

    if args.inplace and args.outputfile:
        print("can only write output file or in-place not both.")
        sys.exit(1)

    if ( args.export_fixture_groups or args.import_fixture_groups) and not args.xls_file:
        print("xls file required to import or export fixture groups.")
        sys.exit(1)

    return args


def main():
    # load a showfile
    args = get_args()
    setup_logging(args)

    #  load the file and expand
    q = QLC(args.showfile)

    if args.export_fixture_groups and args.xls_file:
        q.export_fixture_groups(args.xls_file)
        
    elif args.import_fixture_groups and args.xls_file:
        if not args.inplace or args.outputfile:
            print("importing fixture groups requires output option.")
            sys.exit(1)
        q.import_fixture_groups(args.xls_file)
    if args.expand_fixtures:
        q.expand_fixture_group_capabilities()

    # handle output
    if args.dump:
        q.workspace.dump()

    if args.inplace:
        if not args.overwrite:
           yn = input(f'Overwrite {args.showfile} [yN] ?')
           if 'n' in yn.lower():
               sys.exit(0)
        q.workspace.write(args.showfile) 

    elif args.outputfile:
        logger.debug(f'writing {args.outputfile}...')
        if path.exists(args.outputfile):
            if not args.overwrite:
                yn = input(f'Overwrite {args.outputfile} [yN] ?')
                if 'n' in yn.lower():
                    sys.exit(0)
        q.workspace.write(args.outputfile)


if __name__ == '__main__':
    main()
