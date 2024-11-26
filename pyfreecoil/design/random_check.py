"""
Partial design rule checks:
    - used for the random geometry generation
    - detect most of the obvious design rule violations
    - computational cost is much lower than the full rules
"""

__author__ = "Thomas Guillod"
__copyright__ = "Thomas Guillod - Dartmouth College"
__license__ = "Mozilla Public License Version 2.0"

import numpy as np
import shapely as sha


def _get_trace(coord, layer):
    """
    Get the different traces and the associated layers.
    Split the winding at each layer switch.
    """

    # find the indices of the layer switches (and start/end indices)
    idx_rep = np.flatnonzero(np.diff(layer) != 0)
    idx_rep = np.concatenate(([0], idx_rep+1, [len(layer)]))

    # find the layer number for the different traces
    layer = layer[idx_rep[0:-1]]

    # split the traces at the layer switches
    coord_list = []
    for idx in range(len(layer)):
        coord_list.append(coord[idx_rep[idx]:idx_rep[idx+1]+1])

    # assign to array
    coord = np.empty(len(coord_list), dtype=object)
    coord[:] = coord_list

    return coord, layer


def _get_segment(coord, width):
    """
    Compute the segment lengths for a winding.
    """

    # get length
    segment = np.diff(coord, 1, 0)
    segment = np.hypot(segment[:, 0], segment[:, 1])

    # remove width
    buffer = np.add(width[:-1], width[1:])/2
    segment = segment-buffer

    return segment


def _get_angle(coord, layer):
    """
    Compute the segment angles for a winding.
    """

    # get segments
    segment = np.diff(coord, 1, 0)
    segment_1 = segment[:-1]
    segment_2 = segment[+1:]

    # get angle
    dot_1 = segment_1[:, 0]*segment_2[:, 1]-segment_1[:, 1]*segment_2[:, 0]
    dot_2 = segment_1[:, 0]*segment_2[:, 0]+segment_1[:, 1]*segment_2[:, 1]
    angle = np.arctan2(dot_1, dot_2)

    # get the sharp angle
    angle = np.abs(np.pi-np.abs(angle))

    # find singular angles
    eps = np.finfo(1.0).eps
    singular_1 = np.all(np.abs(segment_1) < eps, axis=1)
    singular_2 = np.all(np.abs(segment_2) < eps, axis=1)
    singular = np.logical_or(singular_1, singular_2)

    # handle singular angles
    angle[singular] = np.pi

    # with a layer switch, the angle is not constrained
    idx = np.diff(layer) != 0
    angle[idx] = np.pi

    return angle


def get_check(data_coil, data_random):
    """
    Partial design rule checks.
    """

    # extract
    limits = data_random["limits"]
    bounds = data_random["bounds"]

    # extract
    segment_min = limits["segment_min"]
    angle_min = limits["angle_min"]
    n_mask_src = bounds["n_mask_src"]
    n_mask_sink = bounds["n_mask_sink"]
    outline = bounds["outline"]
    keepout = bounds["keepout"]

    # extract
    n_wdg = data_coil["n_wdg"]
    coord_wdg = data_coil["coord_wdg"]
    width_wdg = data_coil["width_wdg"]
    layer_wdg = data_coil["layer_wdg"]

    # check
    assert n_wdg >= 2, "invalid design size"

    # check the minimum winding segment lengths
    segment = _get_segment(coord_wdg, width_wdg)
    if np.any(segment < segment_min):
        return False

    # check the minimum winding segment angles
    angle = _get_angle(coord_wdg, layer_wdg)
    if np.any(np.rad2deg(angle) < angle_min):
        return False

    # check if the winding traces have intersections
    (coord_pth, layer_pth) = _get_trace(coord_wdg, layer_wdg)
    for layer_tmp in np.unique(layer_pth):
        # get the traces with the selected layer
        coord_tmp = coord_pth[layer_pth == layer_tmp]
        coord_tmp = coord_tmp.tolist()

        # create a shape from the traces
        obj = sha.MultiLineString(coord_tmp)

        # check for intersections
        if not obj.is_simple:
            return False

    # get the points that should be located inside the outline
    coord_terminal = coord_wdg[n_mask_src:n_wdg-n_mask_sink]
    width_terminal = width_wdg[n_mask_src:n_wdg-n_mask_sink]

    # get thu outline
    outline = sha.Polygon(outline, holes=keepout)

    # get that all the points are inside the outline
    obj = sha.LineString(coord_terminal)
    if not outline.contains(obj):
        return False

    # get that all the pads are inside the outline
    for coord, width in zip(coord_terminal, width_terminal):
        obj = sha.Point(coord).buffer(width/2, quadsegs=16)
        if not outline.contains(obj):
            return False

    return True
