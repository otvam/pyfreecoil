"""
Module for generating random inductor geometries:
    - single mode: fully random design (ignoring the design rules)
    - iter mode: random design generating iteratively (integrating the design rules)
"""

__author__ = "Thomas Guillod"
__copyright__ = "Thomas Guillod - Dartmouth College"
__license__ = "Mozilla Public License Version 2.0"

import numpy as np


class RandomGeometryError(RuntimeError):
    """
    Exception for signaling an invalid geometry.
    """

    pass


def _get_fct_try(n_iter_max, fct_try, args):
    """
    Call a function until successful (or iteration limit is reached).
    """

    # init
    n_iter = 0
    status = False
    output = None

    # try until successful
    while not status:
        try:
            # update counter
            n_iter += 1

            # try function call
            output = fct_try(*args)

            # exit
            break
        except RandomGeometryError:
            # check for iteration limit
            if n_iter >= n_iter_max:
                raise RandomGeometryError("invalid geometry")

    return output


def _get_wdg_merge(dc_list):
    """
    Merge several geometry description together (coordinates, widths, layers).
    """

    # create an empty geometry
    dc_out = {
        "n_wdg": 0,
        "coord_wdg": np.empty((0, 2), dtype=np.float64),
        "width_wdg": np.empty(0, dtype=np.float64),
        "layer_wdg": np.empty(0, dtype=np.int64),
    }

    # merge the provided geometries
    for dc_tmp in dc_list:
        dc_out["n_wdg"] = dc_out["n_wdg"]+dc_tmp["n_wdg"]
        dc_out["coord_wdg"] = np.append(dc_out["coord_wdg"], dc_tmp["coord_wdg"], axis=0)
        dc_out["width_wdg"] = np.append(dc_out["width_wdg"], dc_tmp["width_wdg"], axis=0)
        dc_out["layer_wdg"] = np.append(dc_out["layer_wdg"], dc_tmp["layer_wdg"], axis=0)

    return dc_out


def _get_wdg_insert(dc, dc_add, idx_pts, idx_layer):
    """
    Insert a geometry description at a specified location (coordinates, widths, layers).
    """

    dc_out = {
        "n_wdg": dc["n_wdg"]+dc_add["n_wdg"],
        "coord_wdg": np.insert(dc["coord_wdg"], idx_pts, dc_add["coord_wdg"], axis=0),
        "width_wdg": np.insert(dc["width_wdg"], idx_pts, dc_add["width_wdg"], axis=0),
        "layer_wdg": np.insert(dc["layer_wdg"], idx_layer, dc_add["layer_wdg"], axis=0),
    }

    return dc_out


def _get_wdg_gen(rng, geometry, n_pts, n_layer):
    """
    Generate a fully random geometry description with a given size (coordinates, widths, layers).
    """

    # extract
    x_min = geometry["x_min"]
    x_max = geometry["x_max"]
    y_min = geometry["y_min"]
    y_max = geometry["y_max"]
    width_min = geometry["width_min"]
    width_max = geometry["width_max"]
    layer_list = geometry["layer_list"]

    # generate random geometry
    width = rng.uniform(low=width_min, high=width_max, size=n_pts)
    x = rng.uniform(low=x_min+(width/2), high=x_max-(width/2), size=n_pts)
    y = rng.uniform(low=y_min+(width/2), high=y_max-(width/2), size=n_pts)
    layer = rng.choice(layer_list, size=n_layer)
    coord = np.vstack((x, y)).transpose()

    # assemble
    design = {
        "n_wdg": n_pts,
        "coord_wdg": coord,
        "width_wdg": width,
        "layer_wdg": layer,
    }

    return design


def _get_wdg_terminal(rng, geometry, n_add, bnd_geom):
    """
    Generate a geometry description for a terminal (coordinates, widths, layers).
    The terminal position and size can be partially (or totally) fixed.
    """

    # extract
    x_min = geometry["x_min"]
    x_max = geometry["x_max"]
    y_min = geometry["y_min"]
    y_max = geometry["y_max"]
    width_min = geometry["width_min"]
    width_max = geometry["width_max"]
    layer_list = geometry["layer_list"]

    # extract the provided terminal data
    if n_add == 0:
        coord_tmp = np.empty((0, 2), dtype=object)
        width_tmp = np.empty(0, dtype=object)
        layer_tmp = np.empty(0, dtype=object)
    else:
        coord_tmp = np.array(bnd_geom["coord"], dtype=object)
        width_tmp = np.array(bnd_geom["width"], dtype=object)
        layer_tmp = np.array(bnd_geom["layer"], dtype=object)

    # generate random geometry for the terminal
    width = rng.uniform(low=width_min, high=width_max, size=len(width_tmp))
    x = rng.uniform(low=x_min+(width/2), high=x_max-(width/2), size=len(coord_tmp))
    y = rng.uniform(low=y_min+(width/2), high=y_max-(width/2), size=len(coord_tmp))
    layer = rng.choice(layer_list, size=len(layer_tmp))
    coord = np.vstack((x, y)).transpose()

    # merge the user-specified and random terminal data:
    #   - if the user-specified is finite, use the user-specified value
    #   - if the user-specified is null, replace with the random value
    coord[coord_tmp != None] = coord_tmp[coord_tmp != None]
    width[width_tmp != None] = width_tmp[width_tmp != None]
    layer[layer_tmp != None] = layer_tmp[layer_tmp != None]

    # assemble
    dc = {
        "n_wdg": n_add,
        "coord_wdg": coord,
        "width_wdg": width,
        "layer_wdg": layer,
    }

    return dc


def _get_wdg_init(rng, geometry, n_wdg, n_init):
    """
    Generate a random coil geometry description (coordinates, widths, layers):
        - using the specified terminals (if any)
        - using additional random points
    """

    # extract
    n_add_src = geometry["n_add_src"]
    n_add_sink = geometry["n_add_sink"]
    src_geom = geometry["src_geom"]
    sink_geom = geometry["sink_geom"]

    # generate the fixed terminals
    dc_src = _get_wdg_terminal(rng, geometry, n_add_src, src_geom)
    dc_sink = _get_wdg_terminal(rng, geometry, n_add_sink, sink_geom)

    # get the maximum number of random points
    n_add = n_wdg-n_add_src-n_add_sink

    # get the requested number of random points
    n_add = np.minimum(n_init, n_add)

    # check size
    if n_add <= 0:
        raise RuntimeError("invalid coil size")

    # get the random geometry
    dc = _get_wdg_gen(rng, geometry, n_add, n_add-1)

    # merge with the terminals
    dc = _get_wdg_merge([dc_src, dc, dc_sink])

    return dc


def _get_wdg_add(rng, geometry, dc):
    """
    Add a random point into an existing geometry description (coordinates, widths, layers).
    """

    # extract
    n_add_src = geometry["n_add_src"]
    n_add_sink = geometry["n_add_sink"]

    # extract
    n_wdg = dc["n_wdg"]

    # generate a random point
    dc_add = _get_wdg_gen(rng, geometry, 1, 1)

    # draw a random index to insert the point (cannot be at the terminals)
    idx_insert = rng.choice(np.arange(n_add_src, n_wdg-n_add_sink+1))

    # find the indices where to insert the point
    if idx_insert == n_add_src:
        # insert just after the source terminal
        idx_pts = idx_insert-0
        idx_layer = idx_insert-0
    elif idx_insert == (n_wdg-n_add_sink):
        # insert just after the sink terminal
        idx_pts = idx_insert-0
        idx_layer = idx_insert-1
    else:
        # insert in the middle (draw for the position of the layer switch)
        position = rng.choice([True, False])
        if position:
            idx_pts = idx_insert-0
            idx_layer = idx_insert-0
        else:
            idx_pts = idx_insert-0
            idx_layer = idx_insert-1

    # insert the point
    dc = _get_wdg_insert(dc, dc_add, idx_pts, idx_layer)

    return dc


def _get_wng_add_try(rng, geometry, n_iter_max, fct_check, dc):
    """
    Add a random point into an existing geometry description (coordinates, widths, layers).
    Call a function until successful (or iteration limit is reached).
    """

    # trial function
    def fct_try():
        # try the operation
        dc_tmp = _get_wdg_add(rng, geometry, dc)

        # check the design rules
        status = fct_check(dc_tmp)

        # exit at failure
        if not status:
            raise RandomGeometryError("invalid geometry for add")

        return dc_tmp

    # generate iteratively
    dc = _get_fct_try(n_iter_max, fct_try, [])

    return dc


def _get_wdg_init_try(rng, geometry, n_iter_max, n_wdg, n_init, fct_check):
    """
    Generate a random coil geometry description (coordinates, widths, layers).
    Call a function until successful (or iteration limit is reached).
    """

    # trial function
    def fct_try():
        # try the operation
        dc_tmp = _get_wdg_init(rng, geometry, n_wdg, n_init)

        # check the design rules
        status = fct_check(dc_tmp)

        # exit at failure
        if not status:
            raise RandomGeometryError("invalid geometry for init")

        return dc_tmp

    # generate iteratively
    dc = _get_fct_try(n_iter_max, fct_try, [])

    return dc


def _get_wdg_tree_try(rng, geometry, n_iter_tree, n_iter_fail, n_wdg, fct_check, dc_vec, n_fail):
    """
    Add a random points into an existing geometry description (coordinates, widths, layers).
    Add a point at the time until the desired size is reached (considering the design rules).
    If a point is producing an invalid geometry, delete the point, and retry.
    """

    # check that an initial design exists
    if len(dc_vec) == 0:
        raise RuntimeError("invalid initial design list")

    # extract the last design
    dc_old = dc_vec.pop()
    n_wdg_old = dc_old["n_wdg"]

    # check if the design has the desired size
    if n_wdg_old == n_wdg:
        return dc_old
    else:
        try:
            # try to increase the design size
            dc_new = _get_wng_add_try(rng, geometry, n_iter_tree, fct_check, dc_old)

            # if successful, add the designs to the design list
            dc_vec += [dc_old, dc_new]
        except RandomGeometryError:
            # in case of failure, count the failure
            n_fail += 1

            # prevent a recursive call with an empty design list
            if len(dc_vec) == 0:
                dc_vec += [dc_old]

            # check for failure limit
            if n_fail >= n_iter_fail:
                raise RandomGeometryError("iteration failure")

        # recursive call the increase the design size
        dc_new = _get_wdg_tree_try(rng, geometry, n_iter_tree, n_iter_fail, n_wdg, fct_check, dc_vec, n_fail)

        return dc_new


def get_rand(data_random, fct_check):
    """
    Generate a random inductor geometry:
        - single mode: fully random design (ignoring the design rules)
        - iter mode: random design generating iteratively (integrating the design rules)
    """

    # seed
    rng = np.random.default_rng()

    # extract
    generator = data_random["generator"]
    geometry = data_random["geometry"]

    # extract
    n_wdg_min = generator["n_wdg_min"]
    n_wdg_max = generator["n_wdg_max"]
    n_init_min = generator["n_init_min"]
    n_init_max = generator["n_init_max"]
    n_iter_init = generator["n_iter_init"]
    n_iter_tree = generator["n_iter_tree"]
    n_iter_fail = generator["n_iter_fail"]
    n_iter_reset = generator["n_iter_reset"]
    method = generator["method"]

    # generate the inductor geometry
    if method == "single":
        # draw the number of points
        n_wdg = rng.integers(low=n_wdg_min, high=n_wdg_max+1)

        # generate a fully random coil (ignoring the design rules)
        data_coil = _get_wdg_init(rng, geometry, n_wdg, n_wdg)
    elif method in "iter":
        # function that iteratively generate a random design (integrating the design rules)
        def fct_try(n_wdg_tmp, n_init_tmp):
            dc_tmp = _get_wdg_init_try(rng, geometry, n_iter_init, n_wdg_tmp, n_init_tmp, fct_check)
            dc_tmp = _get_wdg_tree_try(rng, geometry, n_iter_tree, n_iter_fail, n_wdg_tmp, fct_check, [dc_tmp], 0)
            return dc_tmp

        # try to generate a geometry until successful
        while True:
            try:
                # draw the total number of points
                n_wdg = rng.integers(low=n_wdg_min, high=n_wdg_max+1)

                # draw the initial number of points
                n_init = rng.integers(low=n_init_min, high=n_init_max+1)

                # generate iteratively (integrating the design rules)
                data_coil = _get_fct_try(n_iter_reset, fct_try, [n_wdg, n_init])

                # exit
                break
            except RandomGeometryError:
                pass
    else:
        raise ValueError("invalid method")

    return data_coil
