"""
Module for extracting features from the PyPEEC results.
"""

__author__ = "Thomas Guillod"
__copyright__ = "Thomas Guillod - Dartmouth College"
__license__ = "Mozilla Public License Version 2.0"

import numpy as np
import numpy.linalg as lna


def _get_quantile(val, quantile):
    """
    Get the quantile of the norm of a vector.
    """

    # get norm along vector
    val = lna.norm(val, axis=1)

    # get quantile along samples
    val = np.quantile(val, quantile)

    return val


def _get_norm(val, power):
    """
    Get the p-norm value of the norm of a vector.
    The exponent of the p-norm can be selected.
    """

    # get norm along vector
    val = lna.norm(val, axis=1)

    # get p-norm along samples
    val = np.mean(np.power(val, power))
    val = np.power(val, 1/power)

    return val


def _get_value_terminal(source):
    """
    Get the terminal values (current and voltage).
    """

    V = source["winding_src"]["V"]-source["winding_sink"]["V"]
    I = (source["winding_src"]["I"]-source["winding_sink"]["I"])/2

    return V, I


def _get_extract_sweep(data_tmp, processing):
    """
    Extract the solution at a given frequency.
    Extract the inductance and resistance.
    Extract the current density (RMS value).
    Extract the magnetic field (quantile value).
    """

    # extract
    f = data_tmp["freq"]
    var = data_tmp["var"]
    source = data_tmp["source"]

    # extract
    H_qtl = processing["H_qtl"]
    J_pwr = processing["J_pwr"]

    # parse terminal
    (V, I) = _get_value_terminal(source)

    # extract magnetic field (on the point cloud)
    H = var["H_p"]["var"]

    # extract current density (inside the conductors)
    J = var["J_c"]["var"]

    # get impedance
    R = np.real(V/I)
    X = np.imag(V/I)
    L = X/(2*np.pi*f)

    # extract field
    H = _get_quantile(H/I, H_qtl)
    J = _get_norm(J/I, J_pwr)

    return f, R, L, H, J


def _get_mesher(data_voxel):
    """
    Extract features from the mesher data.
    """

    # extract voxel data
    seconds = data_voxel["seconds"]
    data_geom = data_voxel["data_geom"]
    status = data_voxel["status"]

    # check mesher status
    if not status:
        raise RuntimeError("invalid mesher run")

    # extract mesh statistics
    n_total = data_geom["voxel_status"]["n_total"]
    n_used = data_geom["voxel_status"]["n_used"]
    V_total = data_geom["voxel_status"]["V_total"]
    V_used = data_geom["voxel_status"]["V_used"]

    # save the data
    data_mesher = {
        "duration_mesher": seconds,
        "n_total": n_total,
        "n_used": n_used,
        "V_total": V_total,
        "V_used": V_used,
    }

    return data_mesher


def _get_solver(data_solution):
    """
    Extract features from the solver data.
    """

    # extract the data
    seconds = data_solution["seconds"]
    data_init = data_solution["data_init"]
    data_sweep = data_solution["data_sweep"]
    status = data_solution["status"]

    # check status
    assert isinstance(data_init, dict), "invalid solution"
    assert isinstance(data_sweep, dict), "invalid solution"

    # check solver status
    if not status:
        raise RuntimeError("invalid solver run")

    # extract solver statistics
    n_voxel_total = data_init["problem_status"]["n_voxel_total"]
    n_voxel_used = data_init["problem_status"]["n_voxel_used"]
    n_face_total = data_init["problem_status"]["n_face_total"]
    n_face_used = data_init["problem_status"]["n_face_used"]

    # save the data
    data_solver = {
        "duration_solver": seconds,
        "n_voxel_total": n_voxel_total,
        "n_voxel_used": n_voxel_used,
        "n_face_total": n_face_total,
        "n_face_used": n_face_used,
    }

    return data_solver, data_sweep


def _get_matrix(data_sweep, processing):
    """
    Extract the solution at different frequencies.
    """

    # extract
    R_fact = processing["R_fact"]
    L_fact = processing["L_fact"]
    H_fact = processing["H_fact"]
    J_fact = processing["J_fact"]

    # init the frequency-dependent parameters
    f_vec = []
    R_vec = []
    L_vec = []
    J_vec = []
    H_vec = []

    # assign the frequency-dependent parameters
    for data_tmp in data_sweep.values():
        # get field and terminals
        (f, R, L, H, J) = _get_extract_sweep(data_tmp, processing)

        # add solution
        f_vec.append(f)
        R_vec.append(R)
        L_vec.append(L)
        J_vec.append(J)
        H_vec.append(H)

    # save the data
    data_matrix = {
        "f_vec": np.array(f_vec, dtype=np.float64),
        "R_vec": R_fact*np.array(R_vec, dtype=np.float64),
        "L_vec": L_fact*np.array(L_vec, dtype=np.float64),
        "H_vec": H_fact*np.array(H_vec, dtype=np.float64),
        "J_vec": J_fact*np.array(J_vec, dtype=np.float64),
    }

    return data_matrix


def get_final(data_voxel, data_solution, processing):
    """
    Extract features from the PyPEEC results (mesher and solver).
    """

    # extract the mesher data
    data_mesher = _get_mesher(data_voxel)

    # extract the solver data
    (data_solver, data_sweep) = _get_solver(data_solution)

    # extract the solver frequency sweep
    data_matrix = _get_matrix(data_sweep, processing)

    # assemble data
    data_peec = {**data_mesher, **data_solver, **data_matrix}

    return data_peec
