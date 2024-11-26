"""
Module for creating the PyPEEC mesher input data.
Uses the "data_vector" shapes as an input.
"""

__author__ = "Thomas Guillod"
__copyright__ = "Thomas Guillod - Dartmouth College"
__license__ = "Mozilla Public License Version 2.0"

import numpy as np
import shapely as sha


def _get_shape_sub(obj, layer):
    """
    Create a mesher shape data from a single-polygon.
    """

    # check object
    assert isinstance(obj, sha.Polygon), "invalid shape: type"
    assert not obj.is_empty, "invalid shape: empty"
    assert not obj.is_ring, "invalid shape: ring"
    assert obj.is_valid, "invalid shape: invalid"
    assert obj.is_simple, "invalid shape: simple"

    # get exterior
    coord_shell = np.vstack(obj.exterior.xy).transpose()

    # get interiors
    coord_holes = []
    for obj_tmp in obj.interiors:
        coord_holes_tmp = np.vstack(obj_tmp.xy).transpose()
        coord_holes.append(coord_holes_tmp)

    # get layers
    shape_layer = []
    for layer_tmp in layer:
        shape_layer.append("layer_%d" % layer_tmp)

    # get the polygon data
    shape_data = {
        "buffer": None,
        "coord_shell": coord_shell,
        "coord_holes": coord_holes,
    }

    # get the shape data
    shape = {
        "shape_operation": "add",
        "shape_type": "polygon",
        "shape_layer": shape_layer,
        "shape_data": shape_data,
    }

    return shape


def _get_shape(geom):
    """
    Create mesher shape data from a multi-polygon.
    """

    # get data
    layer = geom["layer"]
    obj = geom["obj"]

    # check
    assert isinstance(obj, sha.MultiPolygon), "invalid shape: type"
    assert not obj.is_empty, "invalid shape: empty"
    assert obj.is_valid, "invalid shape: invalid"

    # transform the multi-polygon into a mesher shape data
    shape = []
    for obj_tmp in obj.geoms:
        shape.append(_get_shape_sub(obj_tmp, layer))

    return shape


def _get_geometry_shape(data_vector):
    """
    Get the mesher shape data for the vias, traces, and terminals.
    """

    # extract data
    position = data_vector["position"]
    geom_via = data_vector["geom_via"]
    geom_trace = data_vector["geom_trace"]
    geom_src = data_vector["geom_src"]
    geom_sink = data_vector["geom_sink"]

    # add the terminals
    src = _get_shape(geom_src)
    sink = _get_shape(geom_sink)

    # init the conductor
    cond = []

    # add the vias to the conductor
    for geom in geom_via:
        cond += _get_shape(geom)

    # add the traces to the conductor
    for geom in geom_trace:
        cond += _get_shape(geom)

    # assign shape data
    geometry_shape = {
        "winding_cond": cond,
        "winding_src": src,
        "winding_sink": sink,
    }

    return geometry_shape, position


def _get_voxelize(voxel, mesh, geometry_shape, position):
    """
    Get the mesher voxelization data (from given mesher shape data).
    """

    # extract the data
    cz = mesh["cz"]
    xy_min = mesh["xy_min"]
    xy_max = mesh["xy_max"]
    simplify = mesh["simplify"]
    construct = mesh["construct"]

    # get the voxel size
    (dx, dy, dz) = voxel

    # get voxel parameters
    param = {
        "dx": dx,
        "dy": dy,
        "dz": dz,
        "cz": cz,
        "simplify": simplify,
        "construct": construct,
        "xy_min": xy_min,
        "xy_max": xy_max,
    }

    # construct the layer stack
    layer_stack = []
    for i, position_tmp in enumerate(position):
        tag_layer = "layer_%d" % i
        n_layer = round(position_tmp/dz)
        layer_stack.append({"n_layer": n_layer, "tag_layer": tag_layer})

    # assign the voxelization data
    data_voxelize = {
        "param": param,
        "layer_stack": layer_stack,
        "geometry_shape": geometry_shape,
    }

    return data_voxelize


def _get_domain_data():
    """
    Get the voxel conflict resolution and connection rules.
    """

    # solve conflict (keep terminals, solve the conductor)
    conflict_rules = [
        {"domain_resolve": ["winding_cond"], "domain_keep": ["winding_src"]},
        {"domain_resolve": ["winding_cond"], "domain_keep": ["winding_sink"]},
    ]

    # ensure the terminals and the conductor are connected
    domain_connected = {
        "src": {"domain_group": [["winding_cond"], ["winding_src"]], "connected": True},
        "sink": {"domain_group": [["winding_cond"], ["winding_sink"]], "connected": True},
    }

    # ensure the terminals and the conductor are adjacent
    domain_adjacent = {
        "src": {"domain_group": [["winding_cond", "winding_sink"], ["winding_src"]], "connected": True},
        "sink": {"domain_group": [["winding_cond", "winding_src"], ["winding_sink"]], "connected": True},
    }

    return conflict_rules, domain_connected, domain_adjacent


def _get_pts_vec(span):
    """
    Create a vector for the point cloud definition.
    """

    # extract
    v_min = span["v_min"]
    v_max = span["v_max"]
    n = span["n"]

    # span vector
    vec = np.linspace(v_min, v_max, n)

    return vec


def _get_pts_cloud(cloud):
    """
    Create a point cloud around the component.
    The point cloud is used to compute the magnetic near-field.
    """

    # extract
    x_vec = cloud["x_vec"]
    y_vec = cloud["y_vec"]
    z_max = cloud["z_max"]
    z_min = cloud["z_min"]

    # get vector in all dimensions
    x_vec = _get_pts_vec(x_vec)
    y_vec = _get_pts_vec(y_vec)

    # span the complete point cloud
    (x_mat, y_mat, z_mat) = np.meshgrid(x_vec, y_vec, [z_min, z_max])
    x_mat = x_mat.flatten()
    y_mat = y_mat.flatten()
    z_mat = z_mat.flatten()

    # assemble the point cloud coordinates
    pts_cloud = np.vstack((x_mat, y_mat, z_mat)).transpose()

    return pts_cloud


def get_data(data_vector, voxel, mesh, cloud):
    """
    Create the PyPEEC mesher input data.
    Uses the "data_vector" shapes as an input.
    """

    # use the vector shape mesher
    mesh_type = "shape"

    # get the mesher shape data for the vias, traces, and terminals
    (geometry_shape, position) = _get_geometry_shape(data_vector)

    # get the mesher voxelization data
    data_voxelize = _get_voxelize(voxel, mesh, geometry_shape, position)

    # get the voxel conflict resolution and connection rules
    (conflict_rules, domain_connected, domain_adjacent) = _get_domain_data()

    # generate the point cloud
    pts_cloud = _get_pts_cloud(cloud)

    # define the cloud point
    data_point = {
        "check_cloud": False,
        "full_cloud": False,
        "pts_cloud": pts_cloud,
    }

    # define the conflict resolution
    data_conflict = {
        "resolve_rules": True,
        "resolve_random": True,
        "conflict_rules": conflict_rules,
    }

    # define the integrity checks
    data_integrity = {
        "domain_connected": domain_connected,
        "domain_adjacent": domain_adjacent,
    }

    # define the resampling
    data_resampling = {
        "use_reduce": False,
        "use_resample": False,
        "resampling_factor": [1, 1, 1],
    }

    # assign the mesher input data
    data_geometry = {
        "mesh_type": mesh_type,
        "data_voxelize": data_voxelize,
        "data_resampling": data_resampling,
        "data_conflict": data_conflict,
        "data_integrity": data_integrity,
        "data_point": data_point,
    }

    return data_geometry
