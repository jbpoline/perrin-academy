#!/usr/bin/env python
from __future__ import print_function

DESCRIP = 'exit with 1 if any `.ipynb` notebook file has outputs or prompts'
EPILOG = \
"""
Looks for files in 'searchpath' with extension '.ipynb'. Opens found files as
notebook(s) and checks for code output or prompt numbers.  exits with 1 if
found.  exits with 0 of no outputs found in any notebook
"""
import os
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
    parser.add_argument('searchpath', type=str,
                        help='directory from which to search')
    args = parser.parse_args()
    for dirpath, dirnames, filenames in os.walk(args.searchpath):
        # Omit directories beginning with dots and underscores
        dirnames[:] = [d for d in dirnames
                       if not d.startswith('.') and not d.startswith('_')]
        for fname in filenames:
            if fname.startswith('.'):
                continue
            if not fname.endswith('.ipynb'):
                continue
            fullpath = os.path.join(dirpath, fname)
            with io.open(fullpath, 'r') as f:
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
