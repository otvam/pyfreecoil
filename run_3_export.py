"""
Script for retrieving and exporting inductor designs.

Query the designs from the database.
Write the designs into a dataset file.
The options are specified with command line arguments.
"""

__author__ = "Thomas Guillod"
__copyright__ = "Thomas Guillod - Dartmouth College"
__license__ = "Mozilla Public License Version 2.0"

import sys
import argparse
from config import data_export
from pyfreecoil import export


if __name__ == "__main__":
    # get the parser
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", required=True, type=str, help="filename for the dataset (to be created)")
    parser.add_argument("--name", required=True, type=str, help="name of the study (to be retrieved from the SQL database)")

    # parse arguments
    args = parser.parse_args()
    file = args.file
    name = args.name

    # get the parameters for the export
    export_param = data_export.get_param(name)

    # run workflow
    export.get_run(file, export_param)

    # exit
    sys.exit(0)
