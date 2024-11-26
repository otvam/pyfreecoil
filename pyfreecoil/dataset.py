"""
Module for generating a dataset with many designs:
    - with random geometries
    - with specified geometries

The results are written into a SQL database.

The following parallel processing model is used:
    - the design are generated/computed with multiprocessing
    - a thread is collecting the results and pushing them to the database
"""

__author__ = "Thomas Guillod"
__copyright__ = "Thomas Guillod - Dartmouth College"
__license__ = "Mozilla Public License Version 2.0"

import scilogger
import pandas as pd
from pyfreecoil.design import wrapper_dataset
from pyfreecoil.design import manager_eval
from pyfreecoil.utils import manage_sql
from pyfreecoil.utils import manage_pool

# get logger
LOGGER = scilogger.get_logger(__name__, "planar")


def _run_collect(name, obj_sql, design, n_count, n_total):
    """
    Thread callback function to write the results in the database.
    """

    # count total number of designs
    n_buffer = len(design)

    # convert to dataframe
    design = list(filter(None, design))
    design = pd.DataFrame(design)

    # count number of valid designs
    n_valid = len(design)

    # write the designs to the database
    obj_sql.add_design(name, design)

    # log progress
    with LOGGER.BlockIndent():
        LOGGER.info("buffer = %d / %d - total = %d / %d" % (n_valid, n_buffer, n_count, n_total))


def _get_parameters(obj_wrapper, method_sweep, data_sweep):
    """
    Return a function that will be used to generate the designs.
    Extract parameters for the design generation
    """

    # extract parameters
    if method_sweep == "rand":
        n_run = data_sweep["n_run"]
        cond_gen = data_sweep["cond_gen"]
        cond_solve = data_sweep["cond_solve"]
        obj_keep = data_sweep["obj_keep"]

        fct_compute = obj_wrapper.get_random
        args = ([cond_gen] * n_run, [cond_solve] * n_run, [obj_keep] * n_run)
    elif method_sweep == "array":
        data_coil = data_sweep["data_coil"]
        cond_solve = data_sweep["cond_solve"]
        obj_keep = data_sweep["obj_keep"]

        fct_compute = obj_wrapper.get_fixed
        args = (data_coil, [cond_solve] * len(data_coil), [obj_keep] * len(data_coil))
    else:
        raise ValueError("invalid sweep method")

    return fct_compute, args


def get_run(name, dataset_param):
    """
    Generate a dataset with inductor designs.
    """

    LOGGER.info("====================== START: %s" % name)

    # extract
    data_database = dataset_param["data_database"]
    data_component = dataset_param["data_component"]
    data_tolerance = dataset_param["data_tolerance"]
    data_converter = dataset_param["data_converter"]
    data_objective = dataset_param["data_objective"]
    data_random = dataset_param["data_random"]
    data_dataset = dataset_param["data_dataset"]
    data_sweep = dataset_param["data_sweep"]

    # extract
    method_sweep = data_dataset["method_sweep"]
    delay_collect = data_dataset["delay_collect"]
    delay_timeout = data_dataset["delay_timeout"]
    n_parallel = data_dataset["n_parallel"]

    # wrapper object handling the design generation
    obj_wrapper = wrapper_dataset.DatasetWrapper(
        data_random,
        data_component,
        data_tolerance,
        data_converter,
        data_objective,
    )

    # init sql connection
    LOGGER.info("connect database")
    var_sql = manager_eval.get_var_sql()
    obj_sql = manage_sql.ManageSql(data_database, var_sql, True)
    obj_sql.connect()

    # create a new database study
    LOGGER.info("create study")
    obj_sql.create_study(name)

    # extract parameters for the design generation
    (fct_compute, args) = _get_parameters(obj_wrapper, method_sweep, data_sweep)

    # thread callback function to write the results in the database
    def fct_collect(design, n_count, n_total):
        _run_collect(name, obj_sql, design, n_count, n_total)

    # create a multiprocessing pool
    LOGGER.info("create worker pool")
    obj_pool = manage_pool.QueuePool(n_parallel, delay_collect, delay_timeout, fct_collect, fct_compute)

    # generate the design in parallel
    LOGGER.info("run data")
    obj_pool.get_loop(*args)

    # close the parallel pool and the database
    LOGGER.info("close pool/database")
    obj_pool.close()
    obj_sql.close()

    LOGGER.info("====================== END: %s" % name)
