#!/usr/bin/env python
from __future__ import print_function

DESCRIP = 'run ipython notebook and check for errors'
EPILOG = \
"""
Each cell is submitted to the kernel, and checked for errors.

Thanks MinRK:

https://gist.github.com/minrk/2620876#file-checkipnb-py
"""

import os
from os.path import abspath, dirname, isdir
import sys

from argparse import ArgumentParser, RawDescriptionHelpFormatter

try:
    from IPython.kernel import KernelManager
except ImportError:
    from IPython.zmq.blockingkernelmanager import BlockingKernelManager as KernelManager

from IPython.nbformat.current import reads


class chdir(object):
    """ Change directory to given directory for duration of ``with`` block

    >>> with chdir(path) as cwd:
    ...     # current working directory is `path`
    ...     pass
    """
    def __init__(self, path=None):
        """ Initialize directory context manager

        Parameters
        ----------
        path : str
            path to change directory to, for duration of ``with`` block.
        """
        self.path = abspath(path)

    def __enter__(self):
        self._pwd = abspath(os.getcwd())
        if not isdir(self.path):
            os.mkdir(self.path)
        os.chdir(self.path)
        return self.path

    def __exit__(self, exc, value, tb):
        os.chdir(self._pwd)


def run_notebook(nb):
    km = KernelManager()
    km.start_kernel(stderr=open(os.devnull, 'w'))
    try:
        kc = km.client()
    except AttributeError:
        # 0.13
        kc = km
    kc.start_channels()
    shell = kc.shell_channel
    # simple ping:
    shell.execute("pass")
    shell.get_msg()
    cells = 0
    failures = 0
    for ws in nb.worksheets:
        for cell in ws.cells:
            if cell.cell_type != 'code':
                continue
            shell.execute(cell.input)
            # wait for finish, maximum 20s
            reply = shell.get_msg(timeout=20)['content']
            if reply['status'] == 'error':
                failures += 1
                print("\nFAILURE:")
                print(cell.input)
                print('-----')
                print("raised:")
                print('\n'.join(reply['traceback']))
            print(cell)
            cells += 1
            sys.stdout.write('.')

    print()
    print("ran notebook %s" % nb.metadata.name)
    print("    ran %3i cells" % cells)
    if failures:
        print("    %3i cells raised exceptions" % failures)
    kc.stop_channels()
    km.shutdown_kernel()
    del km

if __name__ == '__main__':
    parser = ArgumentParser(description=DESCRIP,
                            epilog=EPILOG,
                            formatter_class=RawDescriptionHelpFormatter)
    parser.add_argument('filename', type=str, nargs='+',
                        help='notebook filenames')
    args = parser.parse_args()
    for fname in args.filename:
        print("running %s" % fname)
        with open(fname) as f:
            nb = reads(f.read(), 'json')
        with chdir(dirname(fname)):
            run_notebook(nb)
