"""
Script for optimizing inductor designs (shape optimization).

The initial design pool is taken from a SQL database.
The results are written into a SQL database.
The options are specified with command line arguments.
"""

__author__ = "Thomas Guillod"
__copyright__ = "Thomas Guillod - Dartmouth College"
__license__ = "Mozilla Public License Version 2.0"

import sys
import argparse
from config import data_optim
from pyfreecoil import optim


if __name__ == "__main__":
    # get the parser
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", required=True, type=str, help="name of the study (to be created in the SQL database)")
    parser.add_argument("--seed", required=True, type=str, help="name of study with the initial values (in the SQL database)")
    parser.add_argument("--config", required=True, type=str, help="name of the inductor configuration")
    parser.add_argument("--solver", required=True, type=str, help="name of the solver configuration")
    parser.add_argument("--parallel", required=True, type=str, help="number of tasks running in parallel")

    # parse arguments
    args = parser.parse_args()
    name = args.name
    seed = args.seed
    config = args.config
    solver = args.solver
    parallel = args.parallel

    # get the parameters for the inductor shape optimization
    optim_param = data_optim.get_param(config, seed, solver, parallel)

    # run workflow
    optim.get_run(name, optim_param)

    # exit
    sys.exit(0)
