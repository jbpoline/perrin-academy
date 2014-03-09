#!/usr/bin/env python
from __future__ import print_function

DESCRIP = 'exit with 1 if notebook has code outputs '
EPILOG = \
"""
Opens notebook(s) and checks for code output or prompt numbers.  exits with 1
if found 0 otherwise.
"""

import sys

import io

from argparse import ArgumentParser, RawDescriptionHelpFormatter

from IPython.nbformat import current


def cellgen(nb, type=None):
    for ws in nb.worksheets:
        for cell in ws.cells:
            if type is None:
                yield cell
            elif cell.cell_type == type:
                yield cell


def main():
    parser = ArgumentParser(description=DESCRIP,
                            epilog=EPILOG,
                            formatter_class=RawDescriptionHelpFormatter)
    parser.add_argument('filename', type=str, nargs='+',
                        help='notebook filenames')
    args = parser.parse_args()
    for fname in args.filename:
        with io.open(fname, 'r') as f:
            nb = current.read(f, 'json')
        for cell in cellgen(nb, 'code'):
            if hasattr(cell, 'prompt_number'):
                sys.stderr.write(
                    'cell prompt number {0} in {1}\n'.format(
                        cell.prompt_number,
                        fname))
                sys.exit(1)
            if not cell.outputs == []:
                sys.stderr.write('cell output in {0}\n'.format(fname))
                sys.exit(1)


if __name__ == '__main__':
    main()
