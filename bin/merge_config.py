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
import os, os.path, sys, time
import pprint
from xml.etree import ElementTree as et

et.register_namespace('','http://www.qlcplus.org/Workspace')


# add the calling dir as a library dir so we
# don't have to be in it to run
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# append lib dir
sys.path.append(
    os.path.dirname(
        os.path.dirname(
            os.path.abspath(__file__))) + '/lib')

DESC = '''
This tool:
  - reads two showfiles and combines them
'''

# straight from Stack Overflow: http://tinyurl.com/rhlcrlp
class hashabledict(dict):
        def __hash__(self):
            return hash(tuple(sorted(self.items())))


class XMLCombiner(object):
    def __init__(self, filenames):
        assert len(filenames) > 0, 'No filenames!'
        # save all the roots, in order, to be processed later
        self.roots = [et.parse(f).getroot() for f in filenames]

    def combine(self):
        for r in self.roots[1:]:
            # combine each element with the first one, and update that
            self.combine_element(self.roots[0], r)
        # return the string representation
        return et.tostring(self.roots[0])

    def combine_element(self, one, other):
        """
        This function recursively updates either the text or the children
        of an element if another element is found in `one`, or adds it
        from `other` if not found.
        """
        # Create a mapping from tag name to element, as that's what we are fltering with
        mapping = {(el.tag, hashabledict(el.attrib)): el for el in one}
        for el in other:
            if len(el) == 0:
                # Not nested
                try:
                    # Update the text
                    mapping[(el.tag, hashabledict(el.attrib))].text = el.text
                except KeyError:
                    # An element with this name is not in the mapping
                    mapping[(el.tag, hashabledict(el.attrib))] = el
                    # Add it
                    one.append(el)
            else:
                try:
                    # Recursively process the element, and update it in the same way
                    self.combine_element(mapping[(el.tag, hashabledict(el.attrib))], el)
                except KeyError:
                    # Not in the mapping
                    mapping[(el.tag, hashabledict(el.attrib))] = el
                    # Just add it
                    one.append(el)


def get_args():
    ''' read arguments from C/L '''
    parser = argparse.ArgumentParser(
        description=DESC,
        formatter_class=argparse.RawTextHelpFormatter)
    parser.set_defaults(help=False)
    parser.set_defaults(overwrite=False)
    parser.add_argument("-o", "--output-file",
                        type=str, default=None,
                        help="Write to output file")
    parser.add_argument("-F", "--overwrite", action="store_true",
                        help="overwrite existing file")
    parser.add_argument('showfiles', type=str, nargs='+',
                        help='Showfiles to combine')

    args = parser.parse_args()
    if len(args.showfiles) != 2 or args.help:
        parser.print_help()
        sys.exit(0)

    return args


def main():
    ''' main program '''

    # handle args
    args = get_args()

    txt = XMLCombiner((args.showfiles[0], args.showfiles[1])).combine()
    if args.output_file:
        if os.path.isfile(args.output_file) and not args.overwrite:
            print('ERROR: file %s exists, use -F to overwrite.' % 
                  args.outputfile)
            sys.exit(1)
        f = open(args.output_file, 'r')
        f.write(txt)
        f.close()
    else:
        print(txt)

if __name__ == '__main__':
    main()
