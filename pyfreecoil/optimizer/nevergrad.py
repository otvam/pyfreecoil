"""
Global optimization with the "nevergrad" library.
Support parallel computing (multithreading).
Support constraint function (good support).
"""

__author__ = "Thomas Guillod"
__copyright__ = "Thomas Guillod - Dartmouth College"
__license__ = "Mozilla Public License Version 2.0"

import nevergrad
import numpy as np
import concurrent.futures


class SolverConvergenceError(RuntimeError):
    """
    Exception for the solver convergence.
    """

    pass


def _get_fitness(x, obj_eval):
    """
    Call the objective function
    Log the results, show the log results, and check for convergence.
    """

    # cast
    x = np.array(x, dtype=np.float64)

    # eval and log
    obj = obj_eval.eval_obj(x)
    obj_eval.set_obj(x, obj)

    # show log results
    var_list = ["obj_tmp = %.3f" % np.min(obj)]
    obj_eval.get_log(var_list)

    # convergence detection
    status = obj_eval.get_convergence()

    # force termination if convergence is achieved
    if status:
        raise SolverConvergenceError("convergence achieved")

    return obj


def _get_constraints(x, obj_eval):
    """
    Call the constraint function
    Log the results.
    """

    # cast
    x = np.array(x, dtype=np.float64)

    # eval and log
    cond = obj_eval.eval_cond(x)
    obj_eval.set_cond(x, cond)

    # correct sign for nevergrad
    cond = np.negative(cond)

    return cond


def get_solve(n_var, lb, ub, discrete, x_init, obj_init, obj_eval, n_parallel, parameters):
    """
    Call the "nevergrad" global optimizer.
    """

    # extract data
    cond = parameters["cond"]
    recompute = parameters["recompute"]
    algorithm = parameters["algorithm"]
    n_trial = parameters["n_trial"]

    # define variable types and bounds
    var_param = []
    for i in range(n_var):
        var_tmp = nevergrad.p.Scalar(lower=lb[i], upper=ub[i])
        if discrete[i]:
            var_param.append(var_tmp.set_integer_casting())
        else:
            var_param.append(var_tmp)

    # set the parameter space
    parametrization = nevergrad.p.Instrumentation(*var_param)

    # create the optimizer
    solver = nevergrad.optimizers.registry[algorithm]
    optimizer = solver(parametrization=parametrization, budget=n_trial, num_workers=n_parallel)

    # constraint function
    def fct_constraints(trial):
        return _get_constraints(trial[0], obj_eval)

    # objective function
    def fct_fitness(*args):
        return _get_fitness(args, obj_eval)

    # set constraint using the cheap constraint mechanism
    if cond:
        optimizer.parametrization.register_cheap_constraint(fct_constraints)

    # set the initial values
    if recompute:
        for x_init_tmp in x_init:
            optimizer.suggest(*x_init_tmp)
    else:
        for x_init_tmp, obj_tmp in zip(x_init, obj_init):
            optimizer.suggest(*x_init_tmp)
            candidate = optimizer.ask()
            optimizer.tell(candidate, obj_tmp)

    # run the optimizer (with multi-threading)
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=n_parallel) as ex:
            optimizer.minimize(fct_fitness, executor=ex, batch_mode=False)
    except SolverConvergenceError:
        pass
