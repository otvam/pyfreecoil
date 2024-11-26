"""
Global optimization with the "pygad" library.
Support parallel computing (multithreading).
Support constraint function (good support).

The mutation and crossover is done with the constraint function:
    - apply the operator (mutation or crossover) and check the constraints
    - keep the valid individuals (rank by validity score)
    - iterate until a new population is obtained
"""

__author__ = "Thomas Guillod"
__copyright__ = "Thomas Guillod - Dartmouth College"
__license__ = "Mozilla Public License Version 2.0"

import pygad
import numpy as np


def _get_fitness(gad, x, idx, obj_eval):
    """
    Call the objective function
    Log the results.
    """

    # check
    assert isinstance(gad, pygad.GA), "invalid data"
    assert isinstance(x, np.ndarray), "invalid data"
    assert (idx is None) or np.issubdtype(type(idx), np.integer), "invalid data"

    # eval and log
    obj = obj_eval.eval_obj(x)
    obj_eval.set_obj(x, obj)

    # correct sign for pygad
    obj = np.negative(obj)

    return obj


def _get_callback(gad, obj_eval):
    """
    Show the log results and check for convergence
    """

    # check
    assert isinstance(gad, pygad.GA), "invalid data"

    # get the current population
    x_all = gad.population
    n_pop_gen = gad.generations_completed
    obj_last = gad.last_generation_fitness

    # get the validity of the population
    cond = obj_eval.eval_cond(x_all)
    n_pop_fail = np.count_nonzero(cond > 0.0)
    n_pop_valid = np.count_nonzero(cond <= 0.0)

    # get the population objective values
    obj_min = np.min(np.negative(obj_last))
    obj_max = np.max(np.negative(obj_last))
    obj_avg = np.mean(np.negative(obj_last))

    # show log results
    var_list = [
        "obj_avg = %.3f" % obj_avg,
        "obj_min = %.3f" % obj_min,
        "obj_max = %.3f" % obj_max,
        "n_pop_gen = %d" % n_pop_gen,
        "n_pop_valid = %d" % n_pop_valid,
        "n_pop_fail = %d" % n_pop_fail,
    ]
    obj_eval.get_log(var_list)

    # convergence detection
    status = obj_eval.get_convergence()

    # force termination if convergence is achieved
    if status:
        return "stop"
    else:
        return None


def _get_select_update(offspring, cond, n_goal, cond_thr):
    """
    Keep only the best offsprings (with respect to the validity scores)
    """

    # detect duplicates
    matrix = offspring.astype(np.float64)
    (_, idx) = np.unique(matrix, axis=0, return_index=True)

    # remove duplicates
    offspring = offspring[idx]
    cond = cond[idx]

    # split the valid and invalid offsprings
    idx_valid = cond <= cond_thr
    (offspring_valid, offspring_invalid) = (offspring[idx_valid], offspring[~idx_valid])
    (cond_valid, cond_invalid) = (cond[idx_valid], cond[~idx_valid])

    # sort invalid scores (to eliminate the worst constraint violations)
    idx_sort = np.argsort(cond_invalid)
    offspring_invalid = offspring_invalid[idx_sort]
    cond_invalid = cond_invalid[idx_sort]

    # combine offsprings
    offspring = np.concatenate((offspring_valid, offspring_invalid))
    cond = np.concatenate((cond_valid, cond_invalid))

    # keep the best offsprings
    offspring = offspring[0:n_goal]
    cond = cond[0:n_goal]

    return offspring, cond


def _get_retry(fct_gen, obj_eval, cond_iter):
    """
    Apply an operator with constraints:
        - apply the operator and check the constraints
        - keep the valid individuals (rank by validity score)
        - iterate until a new population is obtained
    """

    # extract
    n_retry = cond_iter["n_retry"]
    frac_stop = cond_iter["frac_stop"]
    cond_thr = cond_iter["cond_thr"]

    # apply the operator
    offspring = fct_gen()

    # total number of generated offsprings
    n_goal = len(offspring)

    # compute validity scores
    cond = obj_eval.eval_cond(offspring)
    obj_eval.set_cond(offspring, cond)

    # iterate until the offsprings are good enough
    for _ in range(n_retry):
        # stop if enough offsprings are valid
        n_valid = np.count_nonzero(cond <= cond_thr)
        if (n_valid/n_goal) >= frac_stop:
            break

        # apply the operator
        offspring_add = fct_gen()

        # compute validity scores
        cond_add = obj_eval.eval_cond(offspring_add)
        obj_eval.set_cond(offspring_add, cond_add)

        # merge the new offsprings with the existing ones
        offspring = np.concatenate((offspring, offspring_add))
        cond = np.concatenate((cond, cond_add))

        # keep only the best offsprings (with respect to the validity scores)
        (offspring, cond) = _get_select_update(offspring, cond, n_goal, cond_thr)

    return offspring


def get_solve(n_var, lb, ub, discrete, x_init, obj_eval, n_parallel, parameters):
    """
    Call the "pygad" global optimizer.
    """

    # extract data
    cond = parameters["cond"]
    merge = parameters["merge"]
    n_iter = parameters["n_iter"]
    cond_iter = parameters["cond_iter"]
    precision = parameters["precision"]
    crossover_type = parameters["crossover_type"]
    mutation_type = parameters["mutation_type"]
    parent_selection_type = parameters["parent_selection_type"]
    crossover_probability = parameters["crossover_probability"]
    mutation_probability = parameters["mutation_probability"]
    frac_parents_mating = parameters["frac_parents_mating"]
    frac_elitism = parameters["frac_elitism"]

    # an initial population is required
    assert len(x_init) >= 5, "invalid initial pool"

    # get the number of individuals for mating and elitism
    num_parents_mating = np.round(frac_parents_mating*len(x_init)).astype(np.int64)
    keep_elitism = np.round(frac_elitism*len(x_init)).astype(np.int64)

    # define variable types and bounds
    gene_space = []
    gene_type = []
    for i in range(n_var):
        if discrete[i]:
            gene_type.append(int)
            gene_space.append(np.arange(lb[i], ub[i]+1))
        else:
            gene_type.append([float, precision])
            gene_space.append({'low': lb[i], 'high': ub[i]})

    # objective function
    def fct_fitness(gad, x, idx):
        return _get_fitness(gad, x, idx, obj_eval)

    # callback function
    def fct_callback(gad):
        return _get_callback(gad, obj_eval)

    # create the genetic algorithm
    gad = pygad.GA(
        num_parents_mating=num_parents_mating,
        keep_elitism=keep_elitism,
        mutation_probability=mutation_probability,
        crossover_probability=crossover_probability,
        # custom function
        parent_selection_type=parent_selection_type,
        crossover_type=crossover_type,
        mutation_type=mutation_type,
        # iterations
        num_generations=n_iter,
        initial_population=x_init,
        gene_space=gene_space,
        gene_type=gene_type,
        # fitness
        fitness_func=fct_fitness,
        on_generation=fct_callback,
        # options
        save_solutions=True,
        suppress_warnings=True,
        parallel_processing=['thread', n_parallel],
    )

    # extract the crossover and mutation operators
    fct_crossover_op = gad.crossover
    fct_mutation_op = gad.mutation

    # dummy mutation function (do nothing)
    def fct_mutation_dummy(offspring):
        return offspring

    # crossover function (crossover and mutation with constraints)
    def fct_crossover_merge_cond(parents, offspring_size):
        # trial function for the crossover and mutation
        def fct_gen():
            parents_tmp = parents.copy()
            offspring_tmp = fct_crossover_op(parents_tmp, offspring_size)
            offspring_tmp = fct_mutation_op(offspring_tmp)
            return offspring_tmp

        # iteration with the constraint function
        offspring_ret = _get_retry(fct_gen, obj_eval, cond_iter)

        return offspring_ret

    # mutation function (mutation with constraints)
    def fct_mutation_split_cond(offspring):
        # trial for the mutation
        def fct_gen():
            return fct_mutation_op(offspring.copy())

        # iteration with the constraint function
        offspring_ret = _get_retry(fct_gen, obj_eval, cond_iter)

        return offspring_ret

    # crossover function (crossover with constraints)
    def fct_crossover_split_cond(parents, offspring_size):
        # trial for the crossover
        def fct_gen():
            return fct_crossover_op(parents.copy(), offspring_size)

        # iteration with the constraint function
        offspring_ret = _get_retry(fct_gen, obj_eval, cond_iter)

        return offspring_ret

    # assign new mutation and crossover operators
    if cond:
        if merge:
            # use constraints (mutation and crossover together)
            #   - dummy mutation operators (do nothing)
            #   - apply mutation and crossover
            #   - enforce the constraints iteratively
            gad.mutation = fct_mutation_dummy
            gad.crossover = fct_crossover_merge_cond
        else:
            # use constraints (mutation and crossover separate)
            #   - apply mutation
            #   - enforce the constraints iteratively
            #   - apply crossover
            #   - enforce the constraints iteratively
            gad.mutation = fct_mutation_split_cond
            gad.crossover = fct_crossover_split_cond
    else:
        # keep the original operators (without constraints)
        gad.mutation = fct_mutation_op
        gad.crossover = fct_crossover_op

    # run the optimizer (with multi-threading)
    gad.run()
