"""
Module for optimizing an inductor design:
    - get the optimization boundary conditions
    - compute the constraint function
    - compute the objective function
"""

__author__ = "Thomas Guillod"
__copyright__ = "Thomas Guillod - Dartmouth College"
__license__ = "Mozilla Public License Version 2.0"

from pyfreecoil.design import encoding_design
from pyfreecoil.design import manager_eval


class OptimWrapper:
    """
    Class optimizing and solving designs.
    """

    def __init__(self, data_encoding, data_component, data_tolerance, data_converter, data_objective):
        """
        Constructor.
        """

        self.data_encoding = data_encoding
        self.data_component = data_component
        self.data_tolerance = data_tolerance
        self.data_converter = data_converter
        self.data_objective = data_objective

    def get_cond(self, x, x_fixed):
        """
        Check the design rules and compute the constraint function.
        """

        # decode the design geometry from the design vector
        x = encoding_design.get_expand(x, x_fixed)
        data_coil = encoding_design.get_decode(x, self.data_encoding)

        # cast to full design
        design = manager_eval.get_design_default()
        design = manager_eval.set_data_coil(design, data_coil)

        # check full design rules
        design = manager_eval.get_check(design, self.data_component)
        (cond, design) = manager_eval.get_cond(design, self.data_objective)

        return cond

    def get_obj(self, x, x_fixed, cond_solve, obj_keep):
        """
        Solve a design and compute the objective function.
        """

        # decode the design geometry from the design vector
        x = encoding_design.get_expand(x, x_fixed)
        data_coil = encoding_design.get_decode(x, self.data_encoding)

        # cast to full design
        design = manager_eval.get_design_default()
        design = manager_eval.set_data_coil(design, data_coil)

        # check full design rules
        design = manager_eval.get_check(design, self.data_component)
        (cond, design) = manager_eval.get_cond(design, self.data_objective)

        # solve the problem
        if (cond_solve is None) or (cond <= cond_solve):
            design = manager_eval.get_solve(design, self.data_component, self.data_tolerance)
            design = manager_eval.get_score(design, self.data_converter)

        # compute design
        (obj, design) = manager_eval.get_obj(design, self.data_objective)

        # check validity
        if (obj_keep is not None) and (obj >= obj_keep):
            design = None

        return obj, design


def get_bnd_init(design, data_encoding, data_objective):
    """
    Get the optimization boundary conditions:
        - variable types and bounds
        - fixed/constant variables
        - initial design pool
    """

    # get fixed variables
    x_fixed = encoding_design.get_fixed(data_encoding)

    # get the types and bounds
    bnd = encoding_design.get_bnd(x_fixed, data_encoding)

    # list with the initial design pool
    x_init = []

    # list with the design pool objectives
    obj_init = []

    # resample, encode, and remove fixed variables
    for idx_tmp, design_tmp in design.iterrows():
        (obj_tmp, design_tmp) = manager_eval.get_obj(design_tmp, data_objective)
        data_coil_tmp = manager_eval.get_data_coil(design_tmp)
        data_coil_tmp = encoding_design.get_resample(data_coil_tmp, data_encoding)
        x_init_tmp = encoding_design.get_encode(data_coil_tmp, data_encoding)
        x_init_tmp = encoding_design.get_reduce(x_init_tmp, x_fixed)
        x_init.append(x_init_tmp)
        obj_init.append(obj_tmp)

    return bnd, x_fixed, x_init, obj_init


