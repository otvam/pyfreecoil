"""
Module for creating the PyPEEC solver input data.
"""

__author__ = "Thomas Guillod"
__copyright__ = "Thomas Guillod - Dartmouth College"
__license__ = "Mozilla Public License Version 2.0"

import numpy as np


def _get_base_def():
    """
    Get the material and source definition.
    """

    # conductor and terminal are normal electric domains
    material_def = {
        "winding_cond": {
            "domain_list": ["winding_cond"],
            "material_type": "electric",
            "orientation_type": "isotropic",
            "var_type": "lumped",
        },
        "winding_terminal": {
            "domain_list": ["winding_src", "winding_sink"],
            "material_type": "electric",
            "orientation_type": "isotropic",
            "var_type": "lumped",
        }
    }

    # both the source and the sink are voltage sources
    source_def = {
        "winding_src":  {
            "domain_list": ["winding_src"],
            "source_type": "voltage",
            "var_type": "lumped",
        },
        "winding_sink": {
            "domain_list": ["winding_sink"],
            "source_type": "voltage",
            "var_type": "lumped",
        }
    }

    return material_def, source_def


def _get_single_sweep(mat, src, freq):
    """
    Get solver sweep for a given frequency.
    """

    # extract
    rho_re = mat["rho_re"]
    rho_im = mat["rho_im"]
    V_src = src["V_src"]
    R_src = src["R_src"]
    L_src = src["L_src"]

    # get source impedance
    X_src = 2*np.pi*freq*L_src

    # assign the material conductivity
    material_val = {
        "winding_cond": {"rho_re": rho_re, "rho_im": rho_im},
        "winding_terminal": {"rho_re": rho_re, "rho_im": rho_im},
    }

    # assign the source values and impedances
    source_val = {
        "winding_src": {"V_re": +V_src.real, "V_im": +V_src.imag, "Z_re": R_src, "Z_im": X_src},
        "winding_sink": {"V_re": -V_src.real, "V_im": -V_src.imag, "Z_re": R_src, "Z_im": X_src},
    }

    # create a solver sweep with the specified frequency
    sweep_solver = {
        "init": None,
        "param": {
            "freq": freq,
            "material_val": material_val,
            "source_val": source_val,
        },
    }

    return sweep_solver


def _get_all_sweep(excitation):
    """
    Get the solver frequency sweep.
    """

    # extract
    f_vec = excitation["f_vec"]
    mat = excitation["mat"]
    src = excitation["src"]

    # init the dicts
    sweep_solver = {}

    # create the frequency sweep
    for i, freq in enumerate(f_vec):
        # get sweep name
        tag_sweep = "freq_%d" % i

        # add the sweep
        sweep_solver[tag_sweep] = _get_single_sweep(mat, src, freq)

    return sweep_solver


def get_data(excitation):
    """
    Create the PyPEEC solver input data.
    """

    # get the material and source definition
    (material_def, source_def) = _get_base_def()

    # get the frequency sweep and the values
    sweep_solver = _get_all_sweep(excitation)

    # assign the solver input data
    data_problem = {
        "material_def": material_def,
        "source_def": source_def,
        "sweep_solver": sweep_solver,
    }

    return data_problem
