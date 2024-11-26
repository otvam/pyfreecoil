"""
Global optimization with the "optuna" library.
Support parallel computing (multithreading).
Support constraint function (poor support).
"""

__author__ = "Thomas Guillod"
__copyright__ = "Thomas Guillod - Dartmouth College"
__license__ = "Mozilla Public License Version 2.0"

import warnings
import optuna
import numpy as np

# disable optuna warnings
warnings.filterwarnings("ignore", module="optuna")
warnings.filterwarnings("ignore", module="numpy")


def _get_fitness(n_var, lb, ub, discrete, obj_eval, trial):
    """
    Call the objective function
    Log the results.
    """

    # check
    assert(isinstance(trial, optuna.trial.Trial)), "invalid data"

    # get the sampling point
    x = _get_param_sampling(n_var, lb, ub, discrete, trial)

    # eval and log
    obj = obj_eval.eval_obj(x)
    obj_eval.set_obj(x, obj)

    return obj


def _get_constraints(n_var, lb, ub, discrete, obj_eval, trial):
    """
    Call the constraint function
    Log the results.
    """

    # check
    assert(isinstance(trial, optuna.trial.FrozenTrial)), "invalid data"

    # get the sampling point
    x = _get_param_sampling(n_var, lb, ub, discrete, trial)

    # eval and log
    cond = obj_eval.eval_cond(x)
    obj_eval.set_cond(x, cond)

    # convert to the optuna format
    cond = [cond]

    return cond


def _get_callback(study, trial, obj_eval):
    """
    Show the log results and check for convergence
    """

    # check
    assert(isinstance(study, optuna.study.Study)), "invalid data"
    assert(isinstance(trial, optuna.trial.FrozenTrial)), "invalid data"

    # extract the current trial
    n_gen = trial.number
    obj_tmp = trial.value

    # show log results
    var_list = [
        "obj_tmp = %.3f" % obj_tmp,
        "n_gen = %d" % n_gen
    ]
    obj_eval.get_log(var_list)

    # convergence detection
    status = obj_eval.get_convergence()

    # force termination if convergence is achieved
    if status:
        study.stop()


def _get_param_init(n_var, discrete, x_init):
    """
    Encode an initial value in the optuna format.
    """

    # init optuna parameters
    param = {}

    # set variables into a dict
    for i in range(n_var):
        # cast
        if discrete[i]:
            val_tmp = int(x_init[i])
        else:
            val_tmp = float(x_init[i])

        # assign
        param["x_%d" % i] = val_tmp

    return param


def _get_param_sampling(n_var, lb, ub, discrete, trial):
    """
    Use the optuna sampler to get a single sampling point.
    """

    # init variable array
    x = []

    # set sampled values into an array
    for i in range(n_var):
        # sampling
        if discrete[i]:
            val_tmp = trial.suggest_int("x_%d" % i, lb[i], ub[i])
        else:
            val_tmp = trial.suggest_float("x_%d" % i, lb[i], ub[i])

        # assign
        x.append(val_tmp)

    # cast
    x = np.array(x, dtype=np.float64)

    return x


def get_solve(n_var, lb, ub, discrete, x_init, obj_eval, n_parallel, parameters):
    """
    Call the "optuna" global optimizer.
    """

    # extract data
    cond = parameters["cond"]
    sampler = parameters["sampler"]
    n_trial = parameters["n_trial"]

    # disable optuna log
    optuna.logging.disable_default_handler()

    # constraint function
    def fct_contraints(trial):
        return _get_constraints(n_var, lb, ub, discrete, obj_eval, trial)

    # create a sampler (with/without constraints)
    if sampler == "TPE":
        if cond:
            sampler = optuna.samplers.TPESampler(constraints_func=fct_contraints)
        else:
            sampler = optuna.samplers.TPESampler()
    elif sampler == "CmaEs":
        sampler = optuna.samplers.CmaEsSampler()
    else:
        raise ValueError("invalid sampler")

    # create a study
    study = optuna.create_study(sampler=sampler)

    # set the initial values
    for x_init_tmp in x_init:
        param = _get_param_init(n_var, discrete, x_init_tmp)
        study.enqueue_trial(param)

    # objective function
    def fct_fitness(trial):
        return _get_fitness(n_var, lb, ub, discrete, obj_eval, trial)

    # callback function
    def fct_callback(study, trial):
        return _get_callback(study, trial, obj_eval)

    # run the optimizer (with multi-threading)
    study.optimize(fct_fitness, n_trials=n_trial, n_jobs=n_parallel, callbacks=[fct_callback])
