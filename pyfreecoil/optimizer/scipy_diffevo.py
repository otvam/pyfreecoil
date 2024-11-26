"""
Global optimization with the "scipy/diffevo" library.
Support parallel computing (multithreading).
Support constraint function (poor support).
"""

__author__ = "Thomas Guillod"
__copyright__ = "Thomas Guillod - Dartmouth College"
__license__ = "Mozilla Public License Version 2.0"

import numpy as np
import scipy.optimize as opt


def _get_callback(x, convergence, obj_eval):
    """
    Show the log results and check for convergence
    """

    # check
    assert isinstance(x, np.ndarray), "invalid data"
    assert np.issubdtype(type(convergence), np.floating), "invalid data"

    # show log results
    var_list = ["conv = %.3f" % convergence]
    obj_eval.get_log(var_list)

    # convergence detection
    status = obj_eval.get_convergence()

    # force termination if convergence is achieved
    if status:
        return True
    else:
        return None


def _get_fitness(x, obj_eval):
    """
    Call the objective function
    Log the results.
    """

    # convert to the diffevo format
    x = x.transpose()

    # eval and log
    obj = obj_eval.eval_obj(x)
    obj_eval.set_obj(x, obj)

    return obj


def _get_constraints(x, obj_eval):
    """
    Call the constraint function
    Log the results.
    """

    # convert to the diffevo format
    x = x.transpose()

    # eval and log
    cond = obj_eval.eval_cond(x)
    obj_eval.set_cond(x, cond)

    # convert to the diffevo format
    cond = np.expand_dims(cond, axis=0)

    return cond


def get_solve(n_var, lb, ub, discrete, x_init, obj_eval, parameters):
    """
    Call the "scipy/diffevo" global optimizer.
    """

    # extract data
    cond = parameters["cond"]
    tol_rel = parameters["tol_rel"]
    tol_abs = parameters["tol_abs"]
    n_iter = parameters["n_iter"]

    # an initial population is required
    assert len(x_init) >= 5, "invalid initial pool"

    # define variable types and bounds
    x_bnd = []
    x_type = []
    for i in range(n_var):
        x_bnd.append((lb[i], ub[i]))
        x_type.append(discrete[i])

    # callback function
    def fct_callback(x, convergence=0.0):
        return _get_callback(x, convergence, obj_eval)

    # objective function
    def fct_fitness(x):
        return _get_fitness(x, obj_eval)

    # constraint function
    def fct_constraints(x):
        return _get_constraints(x, obj_eval)

    # set non linear constraints
    if cond:
        obj_cond = opt.NonlinearConstraint(fct_constraints, np.NINF, 0.0)
    else:
        obj_cond = tuple()

    # run the optimizer (with multi-threading)
    opt.differential_evolution(
        fct_fitness,
        x_bnd,
        integrality=x_type,
        init=x_init,
        maxiter=n_iter,
        tol=tol_rel,
        atol=tol_abs,
        polish=False,
        vectorized=True,
        updating="deferred",
        constraints=obj_cond,
        callback=fct_callback,
    )
