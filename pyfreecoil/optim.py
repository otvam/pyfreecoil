"""
Module for optimizing inductor designs (shape optimization).

The initial design pool is taken from a SQL database.
The results are written into a SQL database.

The following parallel processing model is used:
    - the optimization algorithm can be vectorized or multithreaded
    - the vectorized or multithreaded calls are computed with multiprocessing
"""

__author__ = "Thomas Guillod"
__copyright__ = "Thomas Guillod - Dartmouth College"
__license__ = "Mozilla Public License Version 2.0"


import scilogger
import numpy as np
import pandas as pd
from pyfreecoil.design import manager_eval
from pyfreecoil.design import wrapper_optim
from pyfreecoil.utils import manage_sql
from pyfreecoil.utils import manage_pool
from pyfreecoil.optimizer import algorithm

# get logger
LOGGER = scilogger.get_logger(__name__, "planar")


def get_run(name, optim_param):
    """
    Optimize inductor designs (shape optimization).
    """

    LOGGER.info("====================== START: %s" % name)

    # extract
    data_database = optim_param["data_database"]
    data_component = optim_param["data_component"]
    data_tolerance = optim_param["data_tolerance"]
    data_converter = optim_param["data_converter"]
    data_encoding = optim_param["data_encoding"]
    data_objective = optim_param["data_objective"]
    data_optim = optim_param["data_optim"]
    data_solver = optim_param["data_solver"]
    data_filter = optim_param["data_filter"]

    # extract
    n_parallel = data_optim["n_parallel"]
    cond_solve = data_optim["cond_solve"]
    obj_keep = data_optim["obj_keep"]

    # wrapper object handling the constraint and objective functions
    obj_wrapper = wrapper_optim.OptimWrapper(
        data_encoding,
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

    # query designs from the database
    def fct_query(query):
        return obj_sql.get_query(query)

    # filter the obtained dataset
    LOGGER.info("filter dataset")
    design = manager_eval.get_design_filter(fct_query, data_filter)

    # show basic statistics about the initial pool
    LOGGER.info("get statistics")
    with LOGGER.BlockIndent():
        LOGGER.info("n_design = %d" % len(design))
        LOGGER.info("n_valid = %d" % np.count_nonzero(design["cond"] <= 0.0))
        LOGGER.info("n_invalid = %d" % np.count_nonzero(design["cond"] > 0.0))
        LOGGER.info("obj_avg = %.3f" % np.mean(design["obj"]))
        LOGGER.info("obj_min = %.3f" % np.min(design["obj"]))
        LOGGER.info("obj_max = %.3f" % np.max(design["obj"]))

    # get the optimization boundary conditions
    LOGGER.info("get boundary conditions")
    (bnd, x_fixed, x_init, obj_init) = wrapper_optim.get_bnd_init(design, data_encoding, data_objective)

    # create a multiprocessing pool
    LOGGER.info("create worker pool")
    obj_pool_obj = manage_pool.FctPool(n_parallel, obj_wrapper.get_obj)
    obj_pool_cond = manage_pool.FctPool(n_parallel, obj_wrapper.get_cond)

    # parallel function for evaluating the objective function
    #   - evaluate the designs in parallel
    #   - add the designs to the database
    def fct_obj(x_tmp):
        # cast
        x_tmp = np.array(x_tmp, dtype=np.float64)

        # call the objective function with multiprocessing
        if x_tmp.ndim == 1:
            # use the multiprocessing "apply" function
            #   - useful for non-vectorized optimizers
            #   - useful for multithreaded optimizers
            #   - avoid the Python GIL
            (obj_tmp, design_tmp) = obj_pool_obj.get_fct(x_tmp, x_fixed, cond_solve, obj_keep)

            # cast
            design_tmp = list(filter(None, [design_tmp]))
            design_tmp = pd.DataFrame(design_tmp)
        elif x_tmp.ndim == 2:
            if len(x_tmp) == 0:
                obj_tmp = np.empty(0, dtype=np.float64)
                design_tmp = pd.DataFrame()
            else:
                # use the multiprocessing "imap" function
                #   - useful for vectorized optimizers
                #       - useful for vectorized optimizers
                #       - avoid the Python GIL
                x_fixed_mat = np.tile(x_fixed, [len(x_tmp), 1])
                cond_solve_vec = np.tile(cond_solve, len(x_tmp))
                obj_keep_vec = np.tile(obj_keep, len(x_tmp))
                out_tmp = obj_pool_obj.get_loop(x_tmp, x_fixed_mat, cond_solve_vec, obj_keep_vec)
                (obj_tmp, design_tmp) = tuple(zip(*out_tmp))

                # cast
                obj_tmp = np.array(obj_tmp, dtype=np.float64)
                design_tmp = list(filter(None, design_tmp))
                design_tmp = pd.DataFrame(design_tmp)
        else:
            raise ValueError("invalid array size")

        # filter designs and add to database
        obj_sql.add_design(name, design_tmp)

        return obj_tmp

    # parallel function for evaluating the constraint function
    def fct_cond(x_tmp):
        # cast
        x_tmp = np.array(x_tmp, dtype=np.float64)

        # call the constraint function with multiprocessing
        if x_tmp.ndim == 1:
            # use the multiprocessing "apply" function
            #   - useful for non-vectorized optimizers
            #   - useful for multithreaded optimizers
            #   - avoid the Python GIL
            cond_tmp = obj_pool_cond.get_fct(x_tmp, x_fixed)
        elif x_tmp.ndim == 2:
            if len(x_tmp) == 0:
                cond_tmp = np.empty(0, dtype=np.float64)
            else:
                # use the multiprocessing "imap" function
                #   - useful for vectorized optimizers
                #       - useful for vectorized optimizers
                #       - avoid the Python GIL
                x_fixed_mat = np.tile(x_fixed, [len(x_tmp), 1])
                cond_tmp = obj_pool_cond.get_loop(x_tmp, x_fixed_mat)

                # cast
                cond_tmp = np.array(cond_tmp, dtype=np.float64)
        else:
            raise ValueError("invalid array size")

        return cond_tmp

    # run the optimization algorithm
    LOGGER.info("run optimizer")
    algorithm.get_solve(bnd, x_init, obj_init, fct_obj, fct_cond, n_parallel, data_solver)

    # close the parallel pool and the database
    LOGGER.info("close pool/database")
    obj_pool_obj.close()
    obj_pool_cond.close()
    obj_sql.close()

    LOGGER.info("====================== END: %s" % name)
