#!/usr/bin/env python
from __future__ import print_function

DESCRIP = 'clear outputs from notebook and resave'
EPILOG = \
"""
Opens notebook(s) and clears code outputs and prompts, saving over previous
notebook.
"""
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
                del cell['prompt_number']
            cell.outputs = []
        with io.open(fname, 'w') as f:
            current.write(nb, f, 'ipynb')


if __name__ == '__main__':
    main()
