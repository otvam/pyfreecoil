"""
Parameters for optimizing inductor designs (shape optimization).
"""

__author__ = "Thomas Guillod"
__copyright__ = "Thomas Guillod - Dartmouth College"
__license__ = "Mozilla Public License Version 2.0"

from config import data_common


def _get_data_solver(solver):
    """
    Get the options for the shape optimizer.
    """

    # get optimizer name and parameters
    if solver == "diffevo":
        # global optimizer, poor constraint support, extremely poor performance
        method = "diffevo"
        parameters = {
            "cond": True,  # use (or not) the constraint function
            "tol_rel": 1e-6,  # relative convergence tolerance
            "tol_abs": 1e-10,  # absolute convergence tolerance
            "n_iter": int(1e3),  # maximum number of iterations
        }
    elif solver == "optuna":
        # global optimizer, poor constraint support, extremely poor performance
        method = "optuna"
        parameters = {
            "cond": True,  # use (or not) the constraint function
            "sampler": "TPE",  # name of the sampling method ("TPE" or "CmaEs")
            "n_trial": int(10e6),  # maximum number of sampler trials
        }
    elif solver == "nevergrad":
        # global optimizer, good constraint support, good performance
        method = "nevergrad"
        parameters = {
            "recompute": False,  # recompute (or) not the initial designs
            "cond": True,  # use (or not) the constraint function
            "algorithm": "NgIohTuned",  # name of the optimization algorithm
            "n_trial": int(100e3),  # maximum number of sampler trials
        }
    elif solver == "pygad":
        # global optimizer, good constraint support, good performance
        method = "pygad"
        parameters = {
            "cond": True,  # use (or not) the constraint function
            "precision": 6,  # precision for floating point variables
            "parent_selection_type": "sss",  # parent selection method
            "crossover_type": "single_point",  # crossover method
            "mutation_type": "random",  # mutation method
            "crossover_probability": 0.50,  # probability for crossover to occur
            "mutation_probability": 0.08,  # probability for mutation to occur
            "frac_parents_mating": 0.30,  # population selected as parents
            "frac_elitism": 0.1,  # population fraction for elite children
            "n_iter": int(1e3),  # maximum number of generations for the genetic algorithm
            "merge": False,  # enforce the constraints for crossover and mutation together
            "cond_iter": {  # options for the iterative process for enforcing constraints
                "n_retry": 100,  # maximum number of iterations for enforcing constraints
                "frac_stop": 0.90,  # fraction of the population that should be valid
                "cond_thr": 0.0,  # constraint threshold for considering a design valid
            },
        }
    elif solver == "simplex":
        # local optimizer, poor constraint support, very limited performance
        method = "minimize"
        parameters = {
            "algorithm": "Nelder-Mead",  # name of the "scipy/minimize" algorithm
            "recompute": False,  # recompute (or) not the initial designs
            "bounds": True,  # use (or not) bounds for the variables
            "tol": 1e-8,  # relative convergence tolerance
            "options": {  # options passed to the "scipy/minimize" algorithm
                "adaptive": True,  # adapt algorithm parameters to dimensionality of problem
                "maxiter": int(10e3),  # maximum allowed number of iterations
                "xatol": 1e-8,  # absolute error for the input for convergence
                "fatol": 1e-8,  # absolute error for the objective for convergence
            },
        }
    elif solver == "powell":
        # local optimizer, poor constraint support, very limited performance
        method = "minimize"
        parameters = {
            "algorithm": "Powell",  # name of the "scipy/minimize" algorithm
            "recompute": False,  # recompute (or) not the initial designs
            "bounds": True,  # use (or not) bounds for the variables
            "tol": 1e-8,  # relative convergence tolerance
            "options": {  # options passed to the "scipy/minimize" algorithm
                "maxiter": int(10e3),  # maximum allowed number of iterations
                "xtol": 1e-8,  # relative error for the input for convergence
                "ftol": 1e-8,  # relative error for the objective for convergence
            },
        }
    elif solver == "cobyla":
        # local optimizer, poor constraint support, very limited performance
        method = "minimize"
        parameters = {
            "algorithm": "COBYLA",  # name of the "scipy/minimize" algorithm
            "recompute": False,  # recompute (or) not the initial designs
            "bounds": True,  # use (or not) bounds for the variables
            "tol": 1e-8,  # relative convergence tolerance
            "options": {  # options passed to the "scipy/minimize" algorithm
                "maxiter": int(10e3),  # maximum allowed number of iterations
                "rhobeg": 1e-2,  # reasonable initial changes to the variables
                "catol": 1e-3,  # absolute tolerance for constraint violations
            },
        }
    elif solver == "slsqp":
        # local optimizer, poor constraint support, very limited performance
        method = "minimize"
        parameters = {
            "algorithm": "SLSQP",  # name of the "scipy/minimize" algorithm
            "recompute": False,  # recompute (or) not the initial designs
            "bounds": True,  # use (or not) bounds for the variables
            "tol": 1e-8,  # relative convergence tolerance
            "options": {  # options passed to the "scipy/minimize" algorithm
                "maxiter": int(10e3),  # maximum allowed number of iterations
                "ftol": 1e-8,  # relative error for the objective for convergence
                "eps": 1e-2,  # gradient step size
            },
        }
    else:
        raise ValueError("invalid solver")

    # relative improvement on the objective function for convergence
    tol_conv_cmp = 2e-3

    # sliding windows for considering the objective function convergence
    n_eval_conv = int(10e3)

    # minimum number of evaluations before starting the convergence check
    n_eval_init = int(20e3)

    # determine the maximum number of function evaluations
    n_eval_max = int(50e3)

    # convergence data
    convergence = {
        "n_eval_conv": n_eval_conv,
        "n_eval_init": n_eval_init,
        "n_eval_max": n_eval_max,
        "tol_conv_cmp": tol_conv_cmp,
    }

    # solver data
    data_solver = {
        "method": method,
        "parameters": parameters,
        "convergence": convergence,
    }

    return data_solver


def _get_data_filter(seed, solver):
    """
    Get the database queries for getting the initial design pool.
    """

    # get the number of design in the initial pool
    #   - n_obj: designs with the best objective function
    #   - n_eta: designs with the highest total efficiency
    #   - n_ripple: designs with the lowest ripple ratio
    #   - n_rand: fully random designs (to ensure diversity)
    if solver in ["slsqp", "simplex", "cobyla", "powell"]:
        n_obj = 1
        n_eta = 1
        n_ripple = 1
        n_rand = 1
    elif solver in ["pygad", "diffevo"]:
        n_obj = 100
        n_eta = 25
        n_ripple = 25
        n_rand = 100
    elif solver in ["nevergrad", "optuna"]:
        n_obj = 500
        n_eta = 100
        n_ripple = 100
        n_rand = 200
    else:
        raise ValueError("invalid cost")

    # random sorting
    def fct_rand(design):
        return design.sample(frac=1)

    # objective function sorting
    def fct_obj(design):
        return design.sort_values("obj")

    # design ripple ratio sorting
    def fct_ripple(design):
        return design.sort_values("ripple_pkpk")

    # design efficiency sorting
    def fct_eta(design):
        return design.sort_values("eta_tot")

    # dataset query
    #   - database query
    #       - limit: row limit for the query
    #       - offset: row offset for the query
    #       - random: random shuffle of the rows
    #       - name_list: list of study names for querying designs
    #   - query filtering
    #       - fct_process: function for filtering/sorting the designs
    #       - keep: maximum number of designs to be selected (if required)
    #       - order: rule for truncating the designs ("random", "head", or "tail")
    data_filter = [
        {
            "query": {"limit": None, "offset": None, "random": True, "name_list": [seed]},
            "extract": [
                {"order": "random", "keep": n_rand, "fct_process": fct_rand},
                {"order": "head", "keep": n_obj, "fct_process": fct_obj},
                {"order": "tail", "keep": n_eta, "fct_process": fct_eta},
                {"order": "head", "keep": n_ripple, "fct_process": fct_ripple},
            ],
        },
    ]

    return data_filter


def get_param(config, seed, solver, parallel):
    """
    Parameters for optimizing inductor designs (shape optimization).
    """

    # get the inductor parameters
    param = data_common.get_param(config)

    # get database options
    data_database = data_common.get_database()

    # number of parallel processes
    n_parallel = int(parallel)

    # get the options for the shape optimizer
    data_solver = _get_data_solver(solver)

    # get the database queries for getting the initial design pool
    data_filter = _get_data_filter(seed, solver)

    # constraint threshold for solving a design after applying the design rules
    cond_solve = None

    # objective function threshold for writing the designs in the database
    obj_keep = 0.6

    # shape optimizer options
    data_optim = {
        "cond_solve": cond_solve,  # constraint threshold for solving a design after applying the design rules
        "obj_keep": obj_keep,  # objective function threshold for writing the designs in the database
        "n_parallel": n_parallel,  # number of parallel processes
    }

    # append the data
    param["data_optim"] = data_optim
    param["data_solver"] = data_solver
    param["data_filter"] = data_filter
    param["data_database"] = data_database

    return param
