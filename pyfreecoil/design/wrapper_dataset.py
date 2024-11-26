"""
Module for generating an inductor dataset:
    - with random inductor designs
    - with given inductor designs
"""

__author__ = "Thomas Guillod"
__copyright__ = "Thomas Guillod - Dartmouth College"
__license__ = "Mozilla Public License Version 2.0"

from pyfreecoil.design import random_check
from pyfreecoil.design import random_generator
from pyfreecoil.design import manager_eval


class DatasetWrapper:
    """
    Class generating and solving designs.
    """

    def __init__(self, data_random, data_component, data_tolerance, data_converter, data_objective):
        """
        Constructor.
        """

        self.data_random = data_random
        self.data_component = data_component
        self.data_tolerance = data_tolerance
        self.data_converter = data_converter
        self.data_objective = data_objective

    def _check_design(self, data_coil):
        """
        Check the design rules and compute the constraint function.
        """

        # cast to full design
        design = manager_eval.get_design_default()
        design = manager_eval.set_data_coil(design, data_coil)

        # check full design rules
        design = manager_eval.get_check(design, self.data_component)
        (cond, design) = manager_eval.get_cond(design, self.data_objective)

        return cond, design

    def _solve_design(self, cond, design, cond_solve):
        """
        Solve a design and compute the objective function.
        """

        # solve the problem
        if (cond_solve is None) or (cond <= cond_solve):
            design = manager_eval.get_solve(design, self.data_component, self.data_tolerance)
            design = manager_eval.get_score(design, self.data_converter)

        # compute the objective function
        (obj, design) = manager_eval.get_obj(design, self.data_objective)

        return obj, design

    def get_cond(self, data_coil, cond_gen):
        """
        Evaluate the constraint function and determine if an inductor design is valid.
        """

        # run pre-check
        status = random_check.get_check(data_coil, self.data_random)

        # check pre-check results
        if not status:
            return False

        # check full design rules
        (cond, design) = self._check_design(data_coil)

        # check
        status = cond <= cond_gen

        return status

    def get_random(self, cond_gen, cond_solve, obj_keep):
        """
        Generate a random inductor design (integrating the constraints).
        """

        # function for validity checks
        def fct_check(dc_tmp):
            return self.get_cond(dc_tmp, cond_gen)

        # get a random design
        data_coil = random_generator.get_rand(self.data_random, fct_check)

        # check full design rules
        (cond, design) = self._check_design(data_coil)

        # solve the problem
        (obj, design) = self._solve_design(cond, design, cond_solve)

        # check validity
        if (obj_keep is not None) and (obj >= obj_keep):
            design = None

        return design

    def get_fixed(self, data_coil, cond_solve, obj_keep):
        """
        Compute a given inductor design.
        """

        # check full design rules
        (cond, design) = self._check_design(data_coil)

        # solve the problem
        (obj, design) = self._solve_design(cond, design, cond_solve)

        # check validity
        if (obj_keep is not None) and (obj >= obj_keep):
            design = None

        return design
