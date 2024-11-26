"""
Module for encoding/decoding inductor designs into variable vectors:
    - encoding/decoding
    - scaling/unscaling
    - integer/continuous variables
    - handle fixed/constant variables
    - change the number of points (resampling)
"""

__author__ = "Thomas Guillod"
__copyright__ = "Thomas Guillod - Dartmouth College"
__license__ = "Mozilla Public License Version 2.0"

import numpy as np


def _get_variable_zip(n_wdg, x_split):
    """
    Combine several arrays (coordinates, width, layers) into design vector.
    The different components (coordinates, width, layers) are interleaved.
    The interleaving is useful for some optimization algorithms.
    """

    # extract
    (x_wdg, y_wdg, width_wdg, layer_wdg) = x_split

    # combine (interleaved arrays)
    x = np.concatenate(x_split)
    x[0:4*n_wdg-1:4] = x_wdg
    x[1:4*n_wdg-1:4] = y_wdg
    x[2:4*n_wdg-1:4] = width_wdg
    x[3:4*n_wdg-1:4] = layer_wdg

    # check length
    n_var = 4*n_wdg-1
    assert len(x) == n_var, "invalid size"

    return x


def _get_variable_split(n_wdg, x):
    """
    Split a design vector into several arrays (coordinates, width, layers).
    The different components (coordinates, width, layers) are interleaved.
    The interleaving is useful for some optimization algorithms.
    """

    # check length
    n_var = 4*n_wdg-1
    assert len(x) == n_var, "invalid variable size"

    # split (interleaved arrays)
    x_wdg = x[0:4*n_wdg-1:4]
    y_wdg = x[1:4*n_wdg-1:4]
    width_wdg = x[2:4*n_wdg-1:4]
    layer_wdg = x[3:4*n_wdg-1:4]

    # assign
    x_split = (x_wdg, y_wdg, width_wdg, layer_wdg)

    return x_split


def _decode_int(val, val_discrete):
    """
    Decode an integer point array.
    Remap sequential values to discrete values.
    """

    # cast
    val_discrete = np.array(np.round(val_discrete), dtype=np.int64)
    val = np.array(np.round(val), dtype=np.int64)

    # convert to discrete values
    val = val_discrete[val]
    
    return val


def _encode_int(val, val_discrete):
    """
    Encode an integer point array.
    Remap discrete values to sequential values.
    """

    # check that the values are corrects
    assert np.all(np.in1d(val, val_discrete)), "invalid integer encoding"

    # convert to sequential values
    val = np.searchsorted(val_discrete, val)
    
    # cast
    val = val.astype(np.float64)

    return val


def _decode_float(val, val_min, val_max, norm_min, norm_max):
    """
    Decode a floating point array.
    Unscale the array with the provided bounds.
    """

    # cast
    val = np.array(val, dtype=np.float64)

    # unscale
    val = (val-norm_min)/(norm_max-norm_min)
    val = val_min+val*(val_max-val_min)

    return val


def _encode_float(val, val_min, val_max, norm_min, norm_max):
    """
    Encode a floating point array.
    Scale the array with the provided bounds.
    """

    # cast
    val = np.array(val, dtype=np.float64)

    # scale
    val = (val-val_min)/(val_max-val_min)
    val = norm_min+val*(norm_max-norm_min)

    return val


def _get_winding_split(data_coil, n_mask_src, n_mask_sink):
    """
    Add a single point to an inductor design.
    The point is inserted between the longest trace segment.
    """

    # extract
    n_wdg = data_coil["n_wdg"]
    coord_wdg = data_coil["coord_wdg"]
    width_wdg = data_coil["width_wdg"]
    layer_wdg = data_coil["layer_wdg"]

    # find the segment length
    segment = np.diff(coord_wdg, 1, 0)
    distance = np.hypot(segment[:, 0], segment[:, 1])
    buffer = np.add(width_wdg[:-1], width_wdg[1:])/2
    length = distance-buffer

    # fixed terminals cannot be resampled
    if n_mask_src > 0:
        length[:+n_mask_src] = np.NINF
    if n_mask_sink > 0:
        length[-n_mask_sink:] = np.NINF

    # find the index of longest segment
    idx = np.argmax(length)

    # find the properties of the new point
    layer_tmp = layer_wdg[idx]
    coord_tmp = (coord_wdg[idx]+coord_wdg[idx+1])/2
    width_tmp = (width_wdg[idx]+width_wdg[idx+1])/2

    # insert the resampled point
    layer_wdg = np.insert(layer_wdg, idx+1, layer_tmp)
    width_wdg = np.insert(width_wdg, idx+1, width_tmp)
    coord_wdg = np.insert(coord_wdg, idx+1, coord_tmp, axis=0)

    # update the number of points
    n_wdg += 1

    # update geometry
    data_coil["n_wdg"] = n_wdg
    data_coil["coord_wdg"] = coord_wdg
    data_coil["width_wdg"] = width_wdg
    data_coil["layer_wdg"] = layer_wdg

    return data_coil


def get_fixed(data_encoding):
    """
    Get the values of the fixed/constant variables.
    Fixed terminals are created non-free variables.
    These variables have constant values.
    """

    # extract
    n_wdg = data_encoding["n_wdg"]
    n_add_src = data_encoding["n_add_src"]
    n_add_sink = data_encoding["n_add_sink"]
    src_geom = data_encoding["src_geom"]
    sink_geom = data_encoding["sink_geom"]
    norm_min = data_encoding["norm_min"]
    norm_max = data_encoding["norm_max"]
    layer_list = data_encoding["layer_list"]
    width_min = data_encoding["width_min"]
    width_max = data_encoding["width_max"]
    x_min = data_encoding["x_min"]
    x_max = data_encoding["x_max"]
    y_min = data_encoding["y_min"]
    y_max = data_encoding["y_max"]

    # init coil data
    coord_wdg = np.full((n_wdg, 2), None, dtype=object)
    width_wdg = np.full(n_wdg, None, dtype=object)
    layer_wdg = np.full(n_wdg-1, None, dtype=object)

    # assign fixed source terminal
    if n_add_src > 0:
        coord_wdg[:+n_add_src] = src_geom["coord"]
        width_wdg[:+n_add_src] = src_geom["width"]
        layer_wdg[:+n_add_src] = src_geom["layer"]

    # assign fixed sink terminal
    if n_add_sink > 0:
        coord_wdg[-n_add_sink:] = sink_geom["coord"]
        width_wdg[-n_add_sink:] = sink_geom["width"]
        layer_wdg[-n_add_sink:] = sink_geom["layer"]

    # extract coordinates
    x_wdg = coord_wdg[:, 0]
    y_wdg = coord_wdg[:, 1]

    # encode/scale fixed variables
    x_wdg[x_wdg != None] = _encode_float(x_wdg[x_wdg != None], x_min, x_max, norm_min, norm_max)
    y_wdg[y_wdg != None] = _encode_float(y_wdg[y_wdg != None], y_min, y_max, norm_min, norm_max)
    width_wdg[width_wdg != None] = _encode_float(width_wdg[width_wdg != None], width_min, width_max, norm_min, norm_max)
    layer_wdg[layer_wdg != None] = _encode_int(layer_wdg[layer_wdg != None], layer_list)

    # combine into a single vector
    x_split = (x_wdg, y_wdg, width_wdg, layer_wdg)
    x_fixed = _get_variable_zip(n_wdg, x_split)

    # cast to float (free variables are NaNs)
    x_fixed = x_fixed.astype(np.float64)

    return x_fixed


def get_resample(data_coil, data_encoding):
    """
    Resample an inductor design to a given size.
    Increase (if required) the number of points describing a design.
    New points are iteratively inserted between the longest trace segments.
    """

    # extract
    n_wdg = data_encoding["n_wdg"]
    n_mask_src = data_encoding["n_mask_src"]
    n_mask_sink = data_encoding["n_mask_sink"]

    # number of points for the provided designs
    n_wdg_tmp = data_coil["n_wdg"]

    # resampling can only increase the number of points
    assert n_wdg_tmp <= n_wdg, "invalid number of points"

    # resample until the specified number of points is reached
    while n_wdg_tmp < n_wdg:
        data_coil = _get_winding_split(data_coil, n_mask_src, n_mask_sink)
        n_wdg_tmp = data_coil["n_wdg"]

    # check that the number of points is correct
    assert n_wdg_tmp == n_wdg, "invalid number of points"

    return data_coil


def get_bnd(x_fixed, data_encoding):
    """
    Get the types and bounds of the free variables.
    """

    # extract
    n_wdg = data_encoding["n_wdg"]
    norm_min = data_encoding["norm_min"]
    norm_max = data_encoding["norm_max"]
    layer_list = data_encoding["layer_list"]

    # lower bound
    lb_split = (
        np.full(n_wdg, norm_min),
        np.full(n_wdg, norm_min),
        np.full(n_wdg, norm_min),
        np.zeros(n_wdg-1),
    )
    lb = _get_variable_zip(n_wdg, lb_split)

    # upper bound
    ub_split = (
        np.full(n_wdg, norm_max),
        np.full(n_wdg, norm_max),
        np.full(n_wdg, norm_max),
        np.full(n_wdg-1, len(layer_list)-1),
    )
    ub = _get_variable_zip(n_wdg, ub_split)

    # discrete variables
    discrete_split = (
        np.full(n_wdg, False),
        np.full(n_wdg, False),
        np.full(n_wdg, False),
        np.full(n_wdg-1, True),
    )
    discrete = _get_variable_zip(n_wdg, discrete_split)

    # remove the fixed variables
    idx_var = np.isnan(x_fixed)
    n_var = np.count_nonzero(idx_var)
    discrete = discrete[idx_var]
    lb = lb[idx_var]
    ub = ub[idx_var]

    # assign
    bnd = {
        "n_var": n_var,
        "discrete": discrete,
        "lb": lb,
        "ub": ub,
    }

    return bnd


def get_decode(x, data_encoding):
    """
    Decode a design vector anto inductor design dictionary.
    """

    # extract
    n_wdg = data_encoding["n_wdg"]
    norm_min = data_encoding["norm_min"]
    norm_max = data_encoding["norm_max"]
    layer_list = data_encoding["layer_list"]
    width_min = data_encoding["width_min"]
    width_max = data_encoding["width_max"]
    x_min = data_encoding["x_min"]
    x_max = data_encoding["x_max"]
    y_min = data_encoding["y_min"]
    y_max = data_encoding["y_max"]

    # split the single vector
    x_split = _get_variable_split(n_wdg, x)
    (x_wdg, y_wdg, width_wdg, layer_wdg) = x_split

    # encode/unscale variables
    x_wdg = _decode_float(x_wdg, x_min, x_max, norm_min, norm_max)
    y_wdg = _decode_float(y_wdg, y_min, y_max, norm_min, norm_max)
    width_wdg = _decode_float(width_wdg, width_min, width_max, norm_min, norm_max)
    layer_wdg = _decode_int(layer_wdg, layer_list)

    # combine coordinates
    coord_wdg = np.vstack((x_wdg, y_wdg)).transpose()

    # assemble
    data_coil = {
        "n_wdg": n_wdg,
        "coord_wdg": coord_wdg,
        "width_wdg": width_wdg,
        "layer_wdg": layer_wdg,
    }

    return data_coil


def get_encode(data_coil, data_encoding):
    """
    Encode a inductor design dictionary into a design vector.
    """

    # extract
    n_wdg = data_encoding["n_wdg"]
    norm_min = data_encoding["norm_min"]
    norm_max = data_encoding["norm_max"]
    layer_list = data_encoding["layer_list"]
    width_min = data_encoding["width_min"]
    width_max = data_encoding["width_max"]
    x_min = data_encoding["x_min"]
    x_max = data_encoding["x_max"]
    y_min = data_encoding["y_min"]
    y_max = data_encoding["y_max"]

    # extract
    n_wdg_tmp = data_coil["n_wdg"]
    coord_wdg = data_coil["coord_wdg"]
    width_wdg = data_coil["width_wdg"]
    layer_wdg = data_coil["layer_wdg"]

    # check length
    assert n_wdg == n_wdg_tmp, "invalid geometry size"

    # check length
    assert len(coord_wdg) == n_wdg, "invalid geometry size"
    assert len(width_wdg) == n_wdg, "invalid geometry size"
    assert len(layer_wdg) == (n_wdg-1), "invalid geometry size"

    # extract coordinates
    x_wdg = coord_wdg[:, 0]
    y_wdg = coord_wdg[:, 1]

    # encode/scale variables
    x_wdg = _encode_float(x_wdg, x_min, x_max, norm_min, norm_max)
    y_wdg = _encode_float(y_wdg, y_min, y_max, norm_min, norm_max)
    width_wdg = _encode_float(width_wdg, width_min, width_max, norm_min, norm_max)
    layer_wdg = _encode_int(layer_wdg, layer_list)

    # combine into a single vector
    x_split = (x_wdg, y_wdg, width_wdg, layer_wdg)
    x = _get_variable_zip(n_wdg, x_split)

    return x


def get_reduce(x_all, x_fixed):
    """
    Remove the fixed/constant variables from a design vector.
    """

    # get free and fixed variables
    idx_free = np.isnan(x_fixed)
    idx_fixed = np.isfinite(x_fixed)

    # get free variables
    x_free = x_all[idx_free]
    x_fixed_test = x_all[idx_fixed]
    x_fixed_given = x_fixed[idx_fixed]

    # check that the fixed variables have the correct values
    assert np.allclose(x_fixed_test, x_fixed_given), "invalid fixed variable"

    return x_free


def get_expand(x_free, x_fixed):
    """
    Add the fixed/constant variables from a design vector.
    """

    # get free variables
    idx_free = np.isnan(x_fixed)

    # init array
    x_all = x_fixed.copy()

    # assign free variables
    x_all[idx_free] = x_free

    return x_all
