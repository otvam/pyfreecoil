# PyFreeCoil - Installation

## Technical Details

The main **dependencies**  of **PyFreeCoil** are:
* [PyPEEC](https://pypeec.otvam.ch) - 3D quasi-magnetostatic solver
* [Shapely](https://shapely.readthedocs.io) - 2D geometry manipulation
* [PyVista](https://pyvista.org) - 3D geometry manipulation
* [NumPy](https://numpy.org) - Basic numerical routines
* [SciPy](https://scipy.org) - Basic numerical routines
* [Pandas](https://pandas.pydata.org) - Data analysis and manipulation
* [Psycopg](https://www.psycopg.org) - PostgreSQL database connector
* [Optuna](https://optuna.readthedocs.io) - Optimization algorithms
* [PyGAD](https://pygad.readthedocs.io) - Optimization algorithms
* [Nevergrad](https://facebookresearch.github.io/nevergrad) - Optimization algorithms

The following **configuration** has been tested:
* Linux with x86/x64
* PostgreSQL 14.13
* Miniforge 24.7.1
* Python 3.10

## Installation Procedure

```bash
# create a conda environment with the dependencies
mamba env create -f conda.yaml

# activate the conda environment
mamba activate pyfreecoil

# copy the PostgreSQL default configuration
cp config/database.ini config/private.ini

# set the PostgreSQL credentials
#    - do not add to git
#    - user login/password
#    - server host/port
#    - database name
vim config/private.ini

# export the database credentials
export PYTHONDATABASE="config/private.ini"

# export the logger configuration
export SCILOGGER="config/scilogger.ini"

# reset the database
python run_manage.py --quiet reset

# check the database status
python run_manage.py --quiet stat
```
