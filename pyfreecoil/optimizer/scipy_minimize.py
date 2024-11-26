"""
Local optimization with the "scipy/minimize" library.
No support for parallel computing.
No support for constraint function.
No support for integer variables.
"""

__author__ = "Thomas Guillod"
__copyright__ = "Thomas Guillod - Dartmouth College"
__license__ = "Mozilla Public License Version 2.0"

import numpy as np
import scipy.optimize as opt


class SolverConvergenceError(RuntimeError):
    """
    Exception for the solver convergence.
    """

    pass


def _get_expand(x, ref, discrete):
    """
    Expand an input by adding the discrete variables.
    """

    # start from reference
    xx = ref.copy()

    # replace optim variables
    xx[np.logical_not(discrete)] = x

    return xx


def _get_fitness(x, obj_eval):
    """
    Call the objective function
    Log the results and show the log results.
    """

    # eval
    obj = obj_eval.eval_obj(x)
    obj_eval.set_obj(x, obj)

    # log
    var_list = ["obj_tmp = %.3f" % np.min(obj)]
    obj_eval.get_log(var_list)

    return obj


def _get_convergence(obj_eval):
    """
    Check for convergence.
    """

    # convergence detection
    status = obj_eval.get_convergence()

    # force termination if convergence is achieved
    if status:
        raise SolverConvergenceError("convergence achieved")


def get_solve(n_var, lb, ub, discrete, x_init, obj_init, obj_eval, parameters):
    """
    Call the "scipy/minimize" local optimizer.
    """

    # extract data
    algorithm = parameters["algorithm"]
    recompute = parameters["recompute"]
    bounds = parameters["bounds"]
    options = parameters["options"]
    tol = parameters["tol"]

    # an initial point is required
    assert len(x_init) >= 1, "invalid initial pool"

    # recompute the initial values
    if recompute:
        obj_init = _get_fitness(x_init, obj_eval)

    # find the best initial point
    idx = np.argmin(obj_init)
    ref = x_init[idx]

    # remove discrete variables
    x_init = ref[np.logical_not(discrete)]

    # define variable bounds for continuous variables
    if bounds:
        x_bnd = []
        for i in range(n_var):
            if not discrete[i]:
                x_bnd.append((lb[i], ub[i]))
    else:
        x_bnd = None

    # fitness function
    def fct_fitness(x_tmp):
        x_tmp = _get_expand(x_tmp, ref, discrete)
        obj_tmp = _get_fitness(x_tmp, obj_eval)
        _get_convergence(obj_eval)
        return obj_tmp

    # run the optimizer
    try:
        opt.minimize(
            fct_fitness,
            x_init,
            tol=tol,
            bounds=x_bnd,
            method=algorithm,
            options=options,
        )
    except SolverConvergenceError:
        pass
