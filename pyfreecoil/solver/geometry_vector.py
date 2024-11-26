"""
Module for creating the shapes and layers composing a winding (traces, vias, and terminals).
Create the "data_vector" shapes (used for the design rule check, the mesher, and the export).

The shape are represented with two different formats:
    - Shapely object (used for the rule check and the mesher)
    - Parametric description (used for CAD and GERBER export)
"""

__author__ = "Thomas Guillod"
__copyright__ = "Thomas Guillod - Dartmouth College"
__license__ = "Mozilla Public License Version 2.0"


import numpy as np
from pyfreecoil.solver import geometry_shape


def _get_add_via(coord, width, layer_start, layer_stop, is_out, is_via):
    """
    Create a via.
    """

    # get the layers
    layer_min = min(layer_start, layer_stop)
    layer_max = max(layer_start, layer_stop)
    layer = np.arange(layer_min+1, layer_max+0)

    # create geometry
    geom = {
        "n_pts": 1,
        "coord": coord,
        "width": width,
        "layer": layer,
        "is_out": is_out,
        "is_via": is_via,
    }

    return geom


def _get_add_trace(n_pts, coord, width, layer, is_out, is_via):
    """
    Create a trace.
    """

    # get layer
    layer = np.array([layer], dtype=np.int64)

    # create geometry
    geom = {
        "n_pts": n_pts,
        "coord": coord,
        "width": width,
        "layer": layer,
        "is_out": is_out,
        "is_via": is_via,
    }

    return geom


def _get_geom_coord(n_wdg, layer_wdg, coord_wdg, width_wdg, terminal):
    """
    Create the shapes (vias and traces) composing a winding.
    """

    # extract data
    n_mask_src = terminal["n_mask_src"]
    n_mask_sink = terminal["n_mask_sink"]

    # flag indicating is the nodes can be located outside the outline
    is_out_wdg = np.full(n_wdg, False)

    # if a mask is used, allow the nodes to be located outside the outline
    if n_mask_src > 0:
        is_out_wdg[:+n_mask_src] = True
    if n_mask_sink > 0:
        is_out_wdg[-n_mask_sink:] = True

    # flag indicating if the nodes contain a via
    is_via_wdg = np.full(n_wdg, True)

    # the terminals cannot contain vias
    is_via_wdg[+0] = False
    is_via_wdg[-1] = False

    # get the indices of the layer switches
    idx_diff = np.flatnonzero(np.diff(layer_wdg))+1
    idx_trace_a = np.concatenate(([0], idx_diff))
    idx_trace_b = np.concatenate((idx_diff, [n_wdg-1]))

    # init list
    geom_trace = []
    geom_via = []

    # get the via coordinates
    for idx in idx_diff:
        # extract data
        coord_tmp = coord_wdg[[idx]]
        width_tmp = width_wdg[[idx]]
        is_out_tmp = is_out_wdg[[idx]]
        is_via_tmp = is_via_wdg[[idx]]
        layer_start = layer_wdg[idx-1]
        layer_stop = layer_wdg[idx-0]

        # add via
        geom_via_tmp = _get_add_via(coord_tmp, width_tmp, layer_start, layer_stop, is_out_tmp, is_via_tmp)
        geom_via.append(geom_via_tmp)

    # get the trace coordinates
    for idx_a, idx_b in zip(idx_trace_a, idx_trace_b):
        # extract data
        n_pts_tmp = idx_b-idx_a+1
        layer_tmp = np.unique(layer_wdg[idx_a:idx_b]).item()
        coord_tmp = coord_wdg[idx_a:idx_b+1]
        width_tmp = width_wdg[idx_a:idx_b+1]
        is_out_tmp = is_out_wdg[idx_a:idx_b+1]
        is_via_tmp = is_via_wdg[idx_a:idx_b+1]

        # no vias inside a trace
        is_via_tmp[+1:-1] = False

        # add trace
        geom_trace_tmp = _get_add_trace(n_pts_tmp, coord_tmp, width_tmp, layer_tmp, is_out_tmp, is_via_tmp)
        geom_trace.append(geom_trace_tmp)

    return geom_via, geom_trace


def _get_terminal_coord(geom_trace, position):
    """
    Create a terminal (source or sink).
    """

    # the terminals are located at the edges
    if position == "src":
        idx = 0
    elif position == "sink":
        idx = -1
    else:
        raise ValueError("invalid terminal position")

    # the terminal data are the same and the end/start of the traces
    is_out = geom_trace[idx]["is_out"][[idx]]
    is_via = geom_trace[idx]["is_via"][[idx]]
    coord = geom_trace[idx]["coord"][[idx]]
    width = geom_trace[idx]["width"][[idx]]
    layer = geom_trace[idx]["layer"]

    # create geometry
    geom_terminal = {
        "n_pts": 1,
        "coord": coord,
        "width": width,
        "layer": layer,
        "is_out": is_out,
        "is_via": is_via,
    }

    return geom_terminal


def _get_shape_assemble(cad_add, cad_sub, cad_mask, construct, simplify):
    """
    Assemble and simplify the shapes
    """

    # cast to shapes
    cad_add = geometry_shape.get_shape(cad_add)
    cad_sub = geometry_shape.get_shape(cad_sub)
    cad_mask = geometry_shape.get_shape(cad_mask)

    # construct
    add = geometry_shape.get_union(cad_add, construct)
    sub = geometry_shape.get_union(cad_sub, construct)
    mask = geometry_shape.get_union(cad_mask, construct)
    obj = geometry_shape.get_difference(add, sub, construct)

    # simplify
    obj = geometry_shape.get_simplify(obj, simplify)
    mask = geometry_shape.get_simplify(mask, simplify)

    return obj, mask


def _get_terminal_size(geom_via, simplify, construct):
    """
    Get the 2D shapes composing a terminal.
    """

    # extract size
    n_pts = geom_via["n_pts"]
    coord = geom_via["coord"]
    width = geom_via["width"]
    is_out = geom_via["is_out"]
    is_via = geom_via["is_via"]

    # a terminal should contain a single node
    assert n_pts == 1, "invalid terminal type"

    # extract
    coord_tmp = coord[0]
    width_tmp = width[0]
    is_out_tmp = is_out[0]
    is_via_tmp = is_via[0]

    # a terminal cannot contain a via
    assert not is_via_tmp, "invalid via type"

    # init the cad shapes
    cad_add = []
    cad_sub = []
    cad_mask = []

    # get the shape
    shape = geometry_shape.get_pad(coord_tmp, width_tmp)

    # add the shape
    cad_add.append(shape)

    # add mask (masks describe the shapes that should be inside the outline)
    if not is_out_tmp:
        cad_mask.append(shape)

    # assemble the shapes
    (obj, mask) = _get_shape_assemble(cad_add, cad_sub, cad_mask, construct, simplify)

    # assign
    geom_via["cad_add"] = cad_add
    geom_via["cad_sub"] = cad_sub
    geom_via["obj"] = obj
    geom_via["mask"] = mask

    return geom_via


def _get_via_size(geom_via, size, simplify, construct):
    """
    Get the 2D shapes composing a via.
    """

    # extract data
    via_hole = size["via_hole"]
    via_clear = size["via_clear"]
    via_plate = size["via_plate"]
    via_min = size["via_min"]

    # extract size
    n_pts = geom_via["n_pts"]
    coord = geom_via["coord"]
    width = geom_via["width"]
    is_out = geom_via["is_out"]
    is_via = geom_via["is_via"]

    # a via should contain a via
    assert n_pts == 1, "invalid terminal type"

    # extract
    coord_tmp = coord[0]
    width_tmp = width[0]
    is_out_tmp = is_out[0]
    is_via_tmp = is_via[0]

    # get via size
    diameter_via = width_tmp-2*via_clear
    diameter_hole = diameter_via-2*via_plate

    # check via status
    assert is_via_tmp, "invalid via type"

    # init the cad shapes
    cad_add = []
    cad_sub = []
    cad_mask = []

    # get the via shapes
    shape_via = geometry_shape.get_pad(coord_tmp, diameter_via)
    shape_hole = geometry_shape.get_pad(coord_tmp, diameter_hole)

    # add the shape
    cad_add.append(shape_via)

    # add mask (masks describe the shapes that should be inside the outline)
    if not is_out_tmp:
        cad_mask.append(shape_via)

    # put a hole in the via (if required)
    if via_hole and (diameter_hole > via_min):
        cad_sub.append(shape_hole)

    # assemble the shapes
    (obj, mask) = _get_shape_assemble(cad_add, cad_sub, cad_mask, construct, simplify)

    # assign
    geom_via["cad_add"] = cad_add
    geom_via["cad_sub"] = cad_sub
    geom_via["obj"] = obj
    geom_via["mask"] = mask

    return geom_via


def _get_trace_size(geom_trace, size, simplify, construct):
    """
    Get the 2D shapes composing a trace.
    """

    # extract data
    via_pad = size["via_pad"]
    via_hole = size["via_hole"]
    via_clear = size["via_clear"]
    via_plate = size["via_plate"]
    via_min = size["via_min"]

    # extract size
    n_pts = geom_trace["n_pts"]
    coord = geom_trace["coord"]
    width = geom_trace["width"]
    is_out = geom_trace["is_out"]
    is_via = geom_trace["is_via"]

    # init the cad shapes
    cad_add = []
    cad_sub = []
    cad_mask = []

    # get the pad coordinates
    for i in range(n_pts):
        # extract
        coord_tmp = coord[i]
        width_tmp = width[i]
        is_out_tmp = is_out[i]
        is_via_tmp = is_via[i]

        # get via size
        diameter_pad = width_tmp+2*via_pad
        diameter_via = width_tmp-2*via_clear
        diameter_hole = diameter_via-2*via_plate

        # handle normal nodes and via nodes
        if is_via_tmp:
            # get the pad shapes
            shape_pad = geometry_shape.get_pad(coord_tmp, diameter_pad)
            shape_hole = geometry_shape.get_pad(coord_tmp, diameter_hole)

            # add the shape
            cad_add.append(shape_pad)

            # add mask (masks describe the shapes that should be inside the outline)
            if not is_out_tmp:
                cad_mask.append(shape_pad)

            # put a hole in the via (if required)
            if via_hole and (diameter_hole > via_min):
                cad_sub.append(shape_hole)
        else:
            # get the pad shape
            shape_pad = geometry_shape.get_pad(coord_tmp, width_tmp)

            # add the shape
            cad_add.append(shape_pad)

            # add mask (masks describe the shapes that should be inside the outline)
            if not is_out_tmp:
                cad_mask.append(shape_pad)

    # get the trace coordinates
    for i in range(n_pts-1):
        # get the trace shape
        shape = geometry_shape.get_trace(coord[i+0], coord[i+1], width[i+0], width[i+1])

        # add the shape
        cad_add.append(shape)

        # add mask (masks describe the shapes that should be inside the outline)
        if (not is_out[i+0]) and (not is_out[i+1]):
            cad_mask.append(shape)

    # assemble the shapes
    (obj, mask) = _get_shape_assemble(cad_add, cad_sub, cad_mask, construct, simplify)

    # assign
    geom_trace["cad_add"] = cad_add
    geom_trace["cad_sub"] = cad_sub
    geom_trace["obj"] = obj
    geom_trace["mask"] = mask

    return geom_trace


def get_data(data_coil, size, terminal, shapely, position, outline, keepout):
    """
    Create the shapes and layers composing a winding (traces, vias, and terminals).
    """

    # extract data
    simplify = shapely["simplify"]
    construct = shapely["construct"]

    # extract data
    n_wdg = data_coil["n_wdg"]
    coord_wdg = data_coil["coord_wdg"]
    layer_wdg = data_coil["layer_wdg"]
    width_wdg = data_coil["width_wdg"]

    # check length
    assert n_wdg >= 2, "invalid geometry size"
    assert len(coord_wdg) == n_wdg, "invalid geometry size"
    assert len(width_wdg) == n_wdg, "invalid geometry size"
    assert len(layer_wdg) == (n_wdg-1), "invalid geometry size"

    # get the traces and vias
    (geom_via, geom_trace) = _get_geom_coord(n_wdg, layer_wdg, coord_wdg, width_wdg, terminal)

    # get the terminals
    geom_src = _get_terminal_coord(geom_trace, "src")
    geom_sink = _get_terminal_coord(geom_trace, "sink")

    # get the 2D via shapes
    for idx, geom_tmp in enumerate(geom_via):
        geom_via[idx] = _get_via_size(geom_tmp, size, simplify, construct)

    # get the 2D trace shapes
    for idx, geom_tmp in enumerate(geom_trace):
        geom_trace[idx] = _get_trace_size(geom_tmp, size, simplify, construct)

    # get the 2D terminal shapes
    geom_src = _get_terminal_size(geom_src, simplify, construct)
    geom_sink = _get_terminal_size(geom_sink, simplify, construct)

    # assign
    data_vector = {
        "position": position,
        "outline": outline,
        "keepout": keepout,
        "geom_trace": geom_trace,
        "geom_via": geom_via,
        "geom_src": geom_src,
        "geom_sink": geom_sink,
    }

    return data_vector
