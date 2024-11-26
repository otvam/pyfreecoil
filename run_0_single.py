"""
Script for computing a single inductor design.

The design geometry are user-defined.
Save the results (data, log, and plots) into files.
The options are specified with command line arguments.
"""

__author__ = "Thomas Guillod"
__copyright__ = "Thomas Guillod - Dartmouth College"
__license__ = "Mozilla Public License Version 2.0"

import sys
import argparse
from config import data_single
from pyfreecoil import eval


if __name__ == "__main__":
    # get the parser
    parser = argparse.ArgumentParser()
    parser.add_argument("--folder", required=True, type=str, help="folder for the results (to be created)")
    parser.add_argument("--config", required=True, type=str, help="name of the inductor configuration")
    parser.add_argument("--shape", required=True, type=str, help="tag specifying the inductor geometry")

    # parse arguments
    args = parser.parse_args()
    folder = args.folder
    config = args.config
    shape = args.shape

    # get the parameters for the evaluation
    eval_param = data_single.get_param(config, shape)

    # run workflow
    eval.get_design(folder, eval_param)

    # exit
    sys.exit(0)
