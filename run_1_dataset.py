"""
Script for generating a dataset with many designs:
    - with random inductor designs
    - with specified inductor designs

The results are written into a SQL database.
The options are specified with command line arguments.
"""

__author__ = "Thomas Guillod"
__copyright__ = "Thomas Guillod - Dartmouth College"
__license__ = "Mozilla Public License Version 2.0"

import sys
import argparse
from config import data_dataset
from pyfreecoil import dataset


if __name__ == "__main__":
    # get the parser
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", required=True, type=str, help="name of the study (to be created in the SQL database)")
    parser.add_argument("--config", required=True, type=str, help="name of the inductor configuration")
    parser.add_argument("--shape", required=True, type=str, help="tag specifying the inductor geometry")
    parser.add_argument("--parallel", required=True, type=str, help="number of tasks running in parallel")

    # parse arguments
    args = parser.parse_args()
    name = args.name
    config = args.config
    shape = args.shape
    parallel = args.parallel

    # get the parameters with the specified inductors
    dataset_param = data_dataset.get_param(config, shape, parallel)

    # run workflow
    dataset.get_run(name, dataset_param)

    # exit
    sys.exit(0)
