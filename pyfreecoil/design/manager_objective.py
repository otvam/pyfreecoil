"""
Module for computing the constraint and objective functions.
"""

__author__ = "Thomas Guillod"
__copyright__ = "Thomas Guillod - Dartmouth College"
__license__ = "Mozilla Public License Version 2.0"

import numpy as np


def get_cond(design, data_objective):
    """
    Compute the scalar constraint function:
        - positive values indicate constraint violations
        - negative values respect the constraints
    """

    # extract
    checked = design["checked"]
    validity_vec = design["validity_vec"]

    # extract
    cond_max = data_objective["cond_max"]
    cond_scale = data_objective["cond_scale"]

    # if no data, use a user-provided worst case
    if not checked:
        cond = cond_max
    else:
        # get the scalar constraint
        #   - using a scaling factor
        #   - if any violation: sum of the violations
        #   - if no violation: most critical case
        if np.any(validity_vec > 0.0):
            cond = cond_scale*np.sum(validity_vec[validity_vec > 0.0])
        else:
            cond = cond_scale*np.max(validity_vec)

        # the violation cannot be worse than the user-provided worst case
        cond = np.minimum(cond, cond_max)

    # assign
    design["cond"] = cond

    return cond, design


def get_obj(design, data_objective):
    """
    Compute the scalar objective function to be minimized:
        - first term: constraint violation
        - second term: losses and penalties
    """

    # extract
    checked = design["checked"]
    solved = design["solved"]
    scored = design["scored"]
    validity_vec = design["validity_vec"]
    penalty_vec = design["penalty_vec"]
    loss_vec = design["loss_vec"]

    # extract
    loss_scale = data_objective["loss_scale"]
    penalty_scale = data_objective["penalty_scale"]
    validity_max = data_objective["validity_max"]
    validity_scale = data_objective["validity_scale"]
    score_scale = data_objective["score_scale"]
    score_max = data_objective["score_max"]

    # if no data, use a user-provided worst case
    if checked:
        # get a scalar value from the constraints
        #   - if any violation: sum of the violations
        #   - if no violation: zero value
        validity = np.sum(validity_vec[validity_vec > 0.0])

        # scale the value
        validity = validity_scale*validity
    else:
        validity = validity_max

    # get objective function
    if solved and scored:
        # get the total losses
        loss = loss_scale*np.sum(loss_vec)

        # get a scalar value from the penalties
        #   - if any violation: sum of the penalties
        #   - if no violation: zero value
        penalty = penalty_scale*np.sum(penalty_vec[penalty_vec > 0.0])

        # combine the losses with the penalty factor
        score = (1.0+penalty)*loss

        # scale the value
        score = score_scale*score
    else:
        score = score_max

    # the violation cannot be worse than the user-provided worst case
    validity = np.minimum(validity, validity_max)
    score = np.minimum(score, score_max)

    # add the constraints and losses/penalties
    obj = validity+score

    # assign
    design["obj"] = obj

    return obj, design
