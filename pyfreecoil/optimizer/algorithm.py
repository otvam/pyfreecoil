"""
Module with a generic interface for optimization algorithms.
    - variable bounds
    - objective function
    - constraint function
    - parallel operation
    - convergence monitoring
"""

__author__ = "Thomas Guillod"
__copyright__ = "Thomas Guillod - Dartmouth College"
__license__ = "Mozilla Public License Version 2.0"

import threading
import scilogger
import numpy as np

# get logger
LOGGER = scilogger.get_logger(__name__, "planar")


class _FunctionEval:
    """
    Monitor the optimizer progress:
        - number of function calls
        - convergence monitoring
        - logging of the progress

    This class is thread-safe but not multiprocessing-safe.
    """

    def __init__(self, fct_obj, fct_cond, convergence):
        """
        Constructor.
        """

        # set functions
        self.fct_obj = fct_obj
        self.fct_cond = fct_cond

        # assign convergence parameters
        self.n_eval_max = convergence["n_eval_max"]
        self.n_eval_conv = convergence["n_eval_conv"]
        self.n_eval_init = convergence["n_eval_init"]
        self.tol_conv_cmp = convergence["tol_conv_cmp"]

        # thread lock semaphore
        self.lock = threading.Semaphore()

        # init counters
        self.n_iter = 0
        self.n_eval_obj = 0
        self.n_eval_cond = 0
        self.n_cond_valid = 0
        self.n_cond_fail = 0

        # init objective array
        self.obj_list = np.empty(0, dtype=np.float64)

        # init best objective
        self.obj_best = np.PINF

    @staticmethod
    def _thread_lock(function):
        """
        Decorator for thread safety.
        """

        def wrap_function(self, *args):
            """
            Acquire the lock and run the decorated function.
            """

            with self.lock:
                return function(self, *args)

        return wrap_function

    def _set_cond_single(self, x, cond):
        """
        Log single call to the constraint function.
        """

        # check data
        assert isinstance(x, np.ndarray), "invalid data"
        assert np.issubdtype(type(cond), np.floating), "invalid data"

        # count call
        self.n_eval_cond += 1

        # check status
        if cond > 0.0:
            self.n_cond_fail += 1
        else:
            self.n_cond_valid += 1

    def _set_obj_single(self, x, obj):
        """
        Log single call to the objective function.
        """

        # check data
        assert isinstance(x, np.ndarray), "invalid data"
        assert np.issubdtype(type(obj), np.floating), "invalid data"

        # count call
        self.n_eval_obj += 1

        # check for improvement
        if obj < self.obj_best:
            self.obj_best = obj

        # log the objective value
        self.obj_list = np.append(self.obj_list, obj)

    def eval_obj(self, x):
        """
        Call the objective function.
        """

        obj = self.fct_obj(x)

        return obj

    def eval_cond(self, x):
        """
        Call the constraint function.
        """

        cond = self.fct_cond(x)

        return cond

    @_thread_lock
    def set_obj(self, x, obj):
        """
        Log several calls to the objective function.
        """

        if np.isscalar(obj):
            self._set_obj_single(x, obj)
        else:
            for x_tmp, obj_tmp in zip(x, obj):
                self._set_obj_single(x_tmp, obj_tmp)

    @_thread_lock
    def set_cond(self, x, cond):
        """
        Log several calls to the constraint function.
        """

        if np.isscalar(cond):
            self._set_cond_single(x, cond)
        else:
            for x_tmp, cond_tmp in zip(x, cond):
                self._set_cond_single(x_tmp, cond_tmp)

    @_thread_lock
    def get_convergence(self):
        """
        Check convergence criteria.
        """

        # check if convergence is forced (number of objective function calls)
        if self.n_eval_obj >= self.n_eval_max:
            LOGGER.info("convergence = %d" % self.n_iter)
            with LOGGER.BlockIndent():
                LOGGER.info("n_eval_obj = %.3f" % self.n_eval_obj)
                LOGGER.info("n_eval_cond = %.3f" % self.n_eval_obj)
                LOGGER.info("obj_best = %.3f" % self.obj_best)

            return True

        # no convergence if the convergence criteria are not defined
        if self.n_eval_conv is None:
            return False
        if self.n_eval_init is None:
            return False
        if self.tol_conv_cmp is None:
            return False

        # check if convergence check is possible (enough objective function calls)
        if self.n_eval_obj < np.maximum(self.n_eval_init, self.n_eval_conv):
            return False

        # get the objective function comparison value
        obj_cmp = np.min(self.obj_list[:-self.n_eval_conv])

        # get the objective function best value
        obj_min = np.min(self.obj_list[-self.n_eval_conv:])

        # compute relative improvement
        tol_obj = (obj_cmp-obj_min)/obj_min

        # check for convergence
        if tol_obj < self.tol_conv_cmp:
            # display convergence
            LOGGER.info("convergence = %d" % self.n_iter)
            with LOGGER.BlockIndent():
                LOGGER.info("n_eval_obj = %.3f" % self.n_eval_obj)
                LOGGER.info("n_eval_cond = %.3f" % self.n_eval_obj)
                LOGGER.info("obj_cmp = %.3f" % obj_cmp)
                LOGGER.info("obj_min = %.3f" % obj_min)
                LOGGER.info("tol_obj = %.3f" % tol_obj)

            return True
        else:
            return False

    @_thread_lock
    def get_log(self, var_list):
        """
        Log the solver progression.
        Additional content can be provided.
        """

        # display
        LOGGER.info("iteration = %d" % self.n_iter)

        # display parameters
        with LOGGER.BlockIndent():
            LOGGER.info("def : n_eval_obj = %d" % self.n_eval_obj)
            LOGGER.info("def : n_eval_cond = %d" % self.n_eval_cond)
            LOGGER.info("def : n_cond_valid = %d" % self.n_cond_valid)
            LOGGER.info("def : n_cond_fail = %d" % self.n_cond_fail)
            LOGGER.info("def : obj_best = %.3f" % self.obj_best)

        # display additional content
        with LOGGER.BlockIndent():
            for var in var_list:
                LOGGER.info("add : " + var)

        # update iter
        self.n_iter += 1


def get_solve(bnd, x_init, obj_init, fct_obj, fct_cond, n_parallel, data_solver):
    """
    Generic interface for optimization algorithms.
    """

    # extract
    n_var = bnd["n_var"]
    discrete = bnd["discrete"]
    lb = bnd["lb"]
    ub = bnd["ub"]

    # extract
    method = data_solver["method"]
    parameters = data_solver["parameters"]
    convergence = data_solver["convergence"]

    LOGGER.info("solver / start")

    # create convergence detection object
    obj_eval = _FunctionEval(fct_obj, fct_cond, convergence)

    # log the initial results
    obj_eval.get_log([])

    # call the corresponding optimization algorithm
    if method == "minimize":
        from pyfreecoil.optimizer import scipy_minimize
        scipy_minimize.get_solve(n_var, lb, ub, discrete, x_init, obj_init, obj_eval, parameters)
    elif method == "diffevo":
        from pyfreecoil.optimizer import scipy_diffevo
        scipy_diffevo.get_solve(n_var, lb, ub, discrete, x_init, obj_eval, parameters)
    elif method == "pygad":
        from pyfreecoil.optimizer import pygad
        pygad.get_solve(n_var, lb, ub, discrete, x_init, obj_eval, n_parallel, parameters)
    elif method == "optuna":
        from pyfreecoil.optimizer import optuna
        optuna.get_solve(n_var, lb, ub, discrete, x_init, obj_eval, n_parallel, parameters)
    elif method == "nevergrad":
        from pyfreecoil.optimizer import nevergrad
        nevergrad.get_solve(n_var, lb, ub, discrete, x_init, obj_init, obj_eval, n_parallel, parameters)
    else:
        raise ValueError("invalid solver")

    # log the final results
    obj_eval.get_log([])

    LOGGER.info("solver / done")
