"""
Module for displaying and serializing inductor design data.
"""

__author__ = "Thomas Guillod"
__copyright__ = "Thomas Guillod - Dartmouth College"
__license__ = "Mozilla Public License Version 2.0"

import numpy as np


def _get_str_clean(arr):
    """
    Remove newline and clean the output of "array2string".
    """

    arr = arr.replace('\n', '')
    arr = arr.replace(' ', '')
    arr = arr.replace(',', ' , ')

    return arr


def _get_str_array(arr, fmt):
    """
    Transform an array into a string with a format specifier.
    """

    # format array
    arr = np.array2string(arr, separator=',', formatter={'all': lambda x: fmt % x})

    # move to single line
    arr = _get_str_clean(arr)

    return arr


def get_disp_str(design):
    """
    Summarize an inductor design with user-friendly strings.
    """

    # init list for the strings
    str_list = []

    # add design IDs info
    str_list.append("serial")
    str_list.append("    study_id = %d" % design["study_id"])
    str_list.append("    design_id = %d" % design["design_id"])

    # extract geometry
    n_wdg = design["n_wdg"]
    coord = design["coord_wdg"]
    width = design["width_wdg"]
    layer = design["layer_wdg"]

    # get the layer of the points
    layer_a = np.concatenate((layer[[0]], layer))
    layer_b = np.concatenate((layer, layer[[-1]]))

    # add the design geometry info
    str_list.append("geometry / n_wdg = %d" % n_wdg)
    iterator = zip(coord, width, layer_a, layer_b)
    for coord_tmp, width_tmp, layer_a_tmp, layer_b_tmp in iterator:
        str_coord = "[%+.3f / %+.3f]" % tuple(1e6*coord_tmp)
        str_width = "%.3f" % (1e6*width_tmp)
        str_layer = "%d:%d" % (layer_a_tmp, layer_b_tmp)
        str_list.append("    %s um / %s um / %s" % (str_coord, str_width, str_layer))

    # add the design rules info
    str_list.append("check")
    str_list.append("    valid_boundary = %.3f" % design["valid_boundary"])
    str_list.append("    valid_clearance = %.3f" % design["valid_clearance"])
    str_list.append("    valid_length = %.3f" % design["valid_length"])
    str_list.append("    valid_width = %.3f" % design["valid_width"])
    str_list.append("    valid_distance = %.3f" % design["valid_distance"])
    str_list.append("    valid_angle = %.3f" % design["valid_angle"])
    str_list.append("    valid_diff = %.3f" % design["valid_diff"])
    str_list.append("    valid_radius = %.3f" % design["valid_radius"])

    # add the PEEC solver info
    str_list.append("peec")
    str_list.append("    f_vec = %s MHz" % _get_str_array(1e-6*design["f_vec"], "%.3f"))
    str_list.append("    R_vec = %s mOhm" % _get_str_array(1e3*design["R_vec"], "%.3f"))
    str_list.append("    L_vec = %s nH" % _get_str_array(1e9*design["L_vec"], "%.3f"))
    str_list.append("    J_vec = %s A/mm2" % _get_str_array(1e-6*design["J_vec"], "%.3f"))
    str_list.append("    H_vec = %s A/m" % _get_str_array(1e0*design["H_vec"], "%.3f"))

    # add the converter operation info
    str_list.append("score")
    str_list.append("    loss")
    str_list.append("        P_sw = %.3f mW" % (1e3*design["P_sw"]))
    str_list.append("        P_add = %.3f mW" % (1e3*design["P_add"]))
    str_list.append("        P_mag = %.3f mW" % (1e3*design["P_mag"]))
    str_list.append("        P_tot = %.3f mW" % (1e3*design["P_tot"]))
    str_list.append("    other")
    str_list.append("        A_sw = %.3f mm2" % (1e6*design["A_sw"]))
    str_list.append("        I_tot = %.3f A" % (1e0*design["I_tot"]))
    str_list.append("        I_pkpk = %.3f A" % (1e0*design["I_pkpk"]))
    str_list.append("        J_tot = %.3f A/mm2" % (1e-6*design["J_tot"]))
    str_list.append("        eta_tot = %.3f %%" % (1e2*design["eta_tot"]))
    str_list.append("        eta_mag = %.3f %%" % (1e2*design["eta_mag"]))
    str_list.append("        ripple_pkpk = %.3f %%" % (1e2*design["ripple_pkpk"]))
    str_list.append("    ac/dc")
    str_list.append("        I_{dc,ac} = %.3f / %.3f A" % (1e0*design["I_dc"], 1e0*design["I_ac"]))
    str_list.append("        P_{dc,ac} = %.3f / %.3f mW" % (1e3*design["P_dc"], 1e3*design["P_ac"]))
    str_list.append("        J_{dc,ac} = %.3f / %.3f A/mm2" % (1e-6*design["J_dc"], 1e-6*design["J_ac"]))
    str_list.append("        H_{dc,ac} = %.3f / %.3f A/m" % (1e0*design["H_dc"], 1e0*design["H_ac"]))

    # add the design status
    str_list.append("status")
    str_list.append("    checked = %s" % design["checked"])
    str_list.append("    solved = %s" % design["solved"])
    str_list.append("    scored = %s" % design["scored"])

    # add vectors with the design performances
    str_list.append("optimization vector")
    str_list.append("    validity_vec = %s" % _get_str_array(design["validity_vec"], "%+.3f"))
    str_list.append("    penalty_vec = %s" % _get_str_array(design["penalty_vec"], "%+.3f"))
    str_list.append("    loss_vec = %s" % _get_str_array(design["loss_vec"], "%+.3f"))

    # add the constraint and objective values
    str_list.append("objective scalar")
    str_list.append("    cond = %+.3f" % design["cond"])
    str_list.append("    obj = %+.3f" % design["obj"])

    return str_list
