"""
Module defining the parameters shared by the different scripts:
    - parameters for the PostgreSQL database
    - parameters for computing inductor designs
"""

__author__ = "Thomas Guillod"
__copyright__ = "Thomas Guillod - Dartmouth College"
__license__ = "Mozilla Public License Version 2.0"


import os
import pathlib
import configparser
import scisave


def get_database():
    """
    Load the database connection parameters:
        - from the default configuration file ("database_default.ini")
        - from a file specified in an environment variable ("PYTHONDATABASE")
    """

    # init parser and set mode to case-sensitive
    parser = configparser.ConfigParser()
    parser.optionxform = str

    # get file custom file
    file = os.getenv("PYTHONDATABASE")
    if file is None:
        raise RuntimeError("database config file is not set: %s" % file)

    # load the config file
    out = parser.read(file)
    if len(out) != 1:
        raise RuntimeError("database file cannot be loaded: %s" % file)

    # extract global parameters
    study = parser.get("GLOBAL", "study")
    design = parser.get("GLOBAL", "design")

    # extract database credential
    credential = {
        "user": parser.get("CREDENTIAL", "user"),
        "password": parser.get("CREDENTIAL", "password"),
        "host": parser.get("CREDENTIAL", "host"),
        "database": parser.get("CREDENTIAL", "database"),
        "port": parser.get("CREDENTIAL", "port"),
    }

    # extract database connection parameters
    connection = {
        "retry": parser.getint("CONNECTION", "retry"),
        "delay": parser.getfloat("CONNECTION", "delay"),
    }

    # extract database session parameters
    session = {
        "readonly": parser.getboolean("SESSION", "readonly"),
        "autocommit": parser.getboolean("SESSION", "autocommit"),
    }

    # assemble data
    data_database = {
        "credential": credential,
        "connection": connection,
        "session": session,
        "study": study,
        "design": design,
    }

    return data_database


def get_param(config):
    """
    Parameters for computing inductor designs.

    The different parameters are defined in YAML files.
    The geometry-dependent values are set with environment variables.
    """

    # check geometry name
    config_list = [
        "floating", "terminal", "field",
        "cutout_keepout", "half_load",
        "three_layer", "three_level",
    ]
    assert config in config_list, "invalid geometry"
    
    # dictionary for the YAML substitutions
    substitute = {}

    # set number of layers for the conductors
    if config == "three_layer":
        # three-layer inductor
        substitute["LAYER_LIST"] = [0, 2, 4]
    else:
        # two-layer inductor
        substitute["LAYER_LIST"] = [0, 4]

    # set inductor geometry outline
    if config == "cutout_keepout":
        # inductor with a complex outline
        substitute["OUTLINE"] = [
            [-0.50e-3, -0.50e-3],
            [-0.15e-3, -0.30e-3],
            [+0.15e-3, -0.30e-3],
            [+0.50e-3, -0.50e-3],
            [+0.50e-3, +0.50e-3],
            [-0.50e-3, +0.50e-3],
        ]

        # inductor with a keepout area
        substitute["KEEPOUT"] = [[
            [-0.15e-3, -0.05e-3],
            [+0.15e-3, -0.05e-3],
            [+0.15e-3, +0.20e-3],
            [-0.15e-3, +0.20e-3],
        ]]
    else:
        # inductor with a simple square outline
        substitute["OUTLINE"] = [
            [-0.5e-3, -0.5e-3],
            [+0.5e-3, -0.5e-3],
            [+0.5e-3, +0.5e-3],
            [-0.5e-3, +0.5e-3],
        ]

        # inductor without a keepout area
        substitute["KEEPOUT"] = []

    # set the terminal position
    if config == "floating":
        # number of nodes (everything is optimized)
        substitute["N_WDG_MIN"] = 6
        substitute["N_WDG_MAX"] = 12
        substitute["N_WDG"] = 12

        # terminal position is free
        substitute["N_ADD_SRC"] = 0
        substitute["N_ADD_SINK"] = 0
        substitute["SRC_GEOM"] = {"coord": [], "width": [], "layer": []}
        substitute["SINK_GEOM"] = {"coord": [], "width": [], "layer": []}

        # all the nodes should be inside the outline
        substitute["N_MASK_SRC"] = 0
        substitute["N_MASK_SINK"] = 0
    else:
        # number of nodes (the terminal placement is not optimized)
        substitute["N_WDG_MIN"] = 10
        substitute["N_WDG_MAX"] = 16
        substitute["N_WDG"] = 16

        # terminal position is constrained
        substitute["N_ADD_SRC"] = 2
        substitute["N_ADD_SINK"] = 2
        substitute["SRC_GEOM"] = {
            "coord": [[+0.1e-3, +0.7e-3], [+0.1e-3, +0.4e-3]],
            "width": [125.0e-6, 125.0e-6],
            "layer": [0, None],
        }
        substitute["SINK_GEOM"] = {
            "coord": [[-0.1e-3, +0.4e-3], [-0.1e-3, +0.7e-3]],
            "width": [125.0e-6, 125.0e-6],
            "layer": [None, 0],
        }

        # the first and last nodes can be located outline the outline
        substitute["N_MASK_SRC"] = 1
        substitute["N_MASK_SINK"] = 1

    # set the penalty limit for the magnetic near-field
    if config == "field":
        # limit the magnetic near-field
        substitute["H_DC_MAX"] = 500.0
        substitute["H_AC_MAX"] = 250.0
    else:
        # magnetic near-field is not constrained
        substitute["H_DC_MAX"] = float("inf")
        substitute["H_AC_MAX"] = float("inf")

    # set the output power of the converter
    if config == "half_load":
        substitute["P_OUT"] = 0.8
    else:
        substitute["P_OUT"] = 1.6

    # set the converter topology and modulation
    if config == "three_level":
        # three-level Buck in CCM/DCM
        substitute["MULTI_LEVEL"] = True
        substitute["FORCE_CCM"] = False
    else:
        # two-level Buck in CCM/DCM
        substitute["MULTI_LEVEL"] = False
        substitute["FORCE_CCM"] = False

    # get YAML file path
    path = pathlib.Path(__file__).parent.resolve()

    # assemble the data
    param = {
        # component
        "data_component": scisave.load_config(
            os.path.join(path, "optim", "component.yaml"),
            extension=True, substitute=substitute,
        ),
        # score
        "data_converter": scisave.load_config(
            os.path.join(path, "optim", "converter.yaml"),
            extension=True, substitute=substitute,
        ),
        # objective
        "data_objective": scisave.load_config(
            os.path.join(path, "optim", "objective.yaml"),
            extension=True, substitute=substitute,
        ),
        # random
        "data_random": scisave.load_config(
            os.path.join(path, "optim", "random.yaml"),
            extension=True, substitute=substitute,
        ),
        # encoding
        "data_encoding": scisave.load_config(
            os.path.join(path, "optim", "encoding.yaml"),
            extension=True, substitute=substitute,
        ),
        # pypeec
        "data_tolerance": scisave.load_config(
            os.path.join(path, "optim", "tolerance.yaml"),
            extension=True, substitute=substitute,
        ),
        "data_viewer": scisave.load_config(
            os.path.join(path, "plotting", "viewer.yaml"),
            extension=True, substitute=substitute,
        ),
        "data_plotter": scisave.load_config(
            os.path.join(path, "plotting", "plotter.yaml"),
            extension=True, substitute=substitute,
        ),
        "data_shaper": scisave.load_config(
            os.path.join(path, "plotting", "shaper.yaml"),
            extension=True, substitute=substitute,
        ),
    }

    return param
