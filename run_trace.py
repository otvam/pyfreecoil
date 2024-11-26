"""
Script for loading traceback files and reproducing the failures.
"""

__author__ = "Thomas Guillod"
__copyright__ = "Thomas Guillod - Dartmouth College"
__license__ = "Mozilla Public License Version 2.0"

import sys
import pathlib
from pyfreecoil import trace


if __name__ == "__main__":
    # get path
    path = pathlib.Path.cwd()

    # run all the traceback files
    for filename in path.glob("trace/*.pck"):
        trace.get_run(filename)

    # exit
    sys.exit(0)
