"""
Script for computing a single inductor design.

Load the design from an exported dataset.
Save the results (data, log, and plots) into files.
The options are specified with command line arguments.
"""

__author__ = "Thomas Guillod"
__copyright__ = "Thomas Guillod - Dartmouth College"
__license__ = "Mozilla Public License Version 2.0"

import sys
import argparse
from config import data_eval
from pyfreecoil import eval


if __name__ == "__main__":
    # get the parser
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", required=True, type=str, help="filename for the dataset (to be loaded)")
    parser.add_argument("--folder", required=True, type=str, help="folder for the results (to be created)")
    parser.add_argument("--config", required=True, type=str, help="name of the inductor configuration")
    parser.add_argument("--extract", required=True, type=str, help="tag specifying the method for extracting a design")

    # parse arguments
    args = parser.parse_args()
    file = args.file
    folder = args.folder
    config = args.config
    extract = args.extract

    # get the parameters for the evaluation
    eval_param = data_eval.get_param(config, extract)

    # run workflow
    eval.get_run(file, folder, eval_param)

    # exit
    sys.exit(0)
