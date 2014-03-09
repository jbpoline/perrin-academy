#!/usr/bin/env python
from __future__ import print_function, absolute_import

DESCRIP = 'clear output, prompts in all `.ipynb` notebook files'
EPILOG = \
"""
Looks for files in 'searchpath' with extension '.ipynb'. Opens found files as
notebook(s) and clears all outputs and prompts, overwriting previous notebook
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
        dirnames[:] = [d for d in dirnames if not d.startswith('.')]
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
                    del cell['prompt_number']
                cell.outputs = []
            with io.open(fullpath, 'w') as f:
                current.write(nb, f, 'ipynb')


if __name__ == '__main__':
    main()
