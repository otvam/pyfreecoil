"""
Script for retrieving and exporting inductor designs.

Query the designs from the database.
Write the designs into a dataset file.
"""

__author__ = "Thomas Guillod"
__copyright__ = "Thomas Guillod - Dartmouth College"
__license__ = "Mozilla Public License Version 2.0"

import scisave
import scilogger
import numpy as np
from pyfreecoil.design import manager_eval
from pyfreecoil.utils import manage_sql

# get logger
LOGGER = scilogger.get_logger(__name__, "planar")


def _get_query(data_database, data_filter):
    """
    Query the design from the database.
    Compute and add missing variables.
    """

    # init sql connection
    LOGGER.info("connect database")
    var_sql = manager_eval.get_var_sql()
    obj_sql = manage_sql.ManageSql(data_database, var_sql, False)
    obj_sql.connect()

    # query designs from the database
    def fct_query(query):
        return obj_sql.get_query(query)

    # filter the obtained dataset
    LOGGER.info("filter dataset")
    design = manager_eval.get_design_filter(fct_query, data_filter)

    # close the database
    LOGGER.info("close database")
    obj_sql.close()

    return design


def _get_write(file, design):
    """
    Write the resulting data into files (DataFrame and CSV).
    """

    # show basic statistics about the dataset
    LOGGER.info("get statistics")
    with LOGGER.BlockIndent():
        LOGGER.info("n_design = %d" % len(design))
        LOGGER.info("n_valid = %d" % np.count_nonzero(design["cond"] <= 0.0))
        LOGGER.info("n_invalid = %d" % np.count_nonzero(design["cond"] > 0.0))
        LOGGER.info("obj_avg = %.3f" % np.mean(design["obj"]))
        LOGGER.info("obj_min = %.3f" % np.min(design["obj"]))
        LOGGER.info("obj_max = %.3f" % np.max(design["obj"]))

    # save the DataFrame
    LOGGER.info("save pck")
    scisave.write_data(file, design)


def get_run(file, export_param):
    """
    Retrieve and export inductor designs from the SQL database
    """

    LOGGER.info("====================== START: %s" % file)

    # extract
    data_database = export_param["data_database"]
    data_filter = export_param["data_filter"]

    # query the dataset
    design = _get_query(data_database, data_filter)

    # check validity
    if design.empty:
        raise RuntimeError("design data is empty")

    # write the dataset
    _get_write(file, design)

    LOGGER.info("====================== END: %s" % file)
