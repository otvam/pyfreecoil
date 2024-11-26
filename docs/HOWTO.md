# PyFreeCoil - Getting Started

## Main Files and Folders

* [conda.yaml](conda.yaml) - Definition of the conda environment used to install the dependencies.
* [run_trace.py](run_trace.py) - Utils for analysing and reproducing failures with traceback files. 
* [run_manage.py](run_manage.py) - Utils for managing the content of the PostgreSQL database.

* [docs](docs) - Folder the documentation and the images.
* [config](config) - Folder containing all the user-defined parameters.
* [pyfreecoil](pyfreecoil) - Folder with the shape optimization code.
* [pypostproc](pypostproc) - Folder with utils to export/plot geometries.

* [run_0_single.py](run_0_single.py) 
    * Script for computing a single inductor design.
    * The design geometry are user-defined. 
    * Save the results (data, log, and plots) into files.
* [run_1_dataset.py](run_1_dataset.py)
    * Script for generating a dataset with many designs.
    * Random inductor designs can be used.
    * User-specified inductor designs can be used.
    * The results are written into a SQL database.
* [run_2_optim.py](run_2_optim.py)
    * Script for optimizing inductor designs (shape optimization).
    * The initial design pool is taken from a SQL database.
    * The results are written into a SQL database.
* [run_3_export.py](run_3_export.py)
    * Script for retrieving and exporting inductor designs.
    * Query the designs from the SQL database.
    * Write the designs into a dataset file.
* [run_4_eval.py](run_4_eval.py)
    * Script for computing a single inductor design.
    * Load the design from an exported dataset.
    * Save the results (data, log, and plots) into files.

## List of Available Inductor Configurations

The following default configuration is considered:
* Two-layer air-core inductor with 1mm x 1mm footprint
* Two level Buck converter (3.3V to 0.8V, 1.6W, and 40.68MHz)

The following variations are available:
* `floating` - inductor with floating terminals
* `terminal` - inductor with fixed terminals
* `field` - inductor with a near-field optimization
* `cutout_keepout` - inductor with a complex footprint
* `three_layer` - extension with a three-layer stack
* `three_level` - extension with three-level converter
* `half_load` - inductor operating at half load

## List of Available Optimization Algorithms

The following local optimizers are available:
* `simplex` - Nelder-Mead simplex (SciPy / minimize)
* `powell` - Powell method (SciPy / minimize)
* `cobyla` - COBYLA method (SciPy / minimize)
* `slsqp` - SLSQP method (SciPy / minimize)

The following global optimizers are available:
* `diffevo` - differential evolution (SciPy / diffevo)
    * poor constraint support
    * extremely poor performance 
* `optuna` - algorithms available through Optuna
    * poor constraint support
    * extremely poor performance 
* `nevergrad` - algorithms available through Nevergrad
    * good constraint support
    * good performance
* `pygad` - constraint-aware genetic algorithm
    * good constraint support
    * good performance

## Tutorial

### Setup

```bash
# create folders for the output data
mkdir -p data_eval
mkdir -p data_export
mkdir -p data_postproc

# activate the conda environment
mamba activate pyfreecoil

# export the database credential
export PYTHONDATABASE="config/private.ini"

# export the logger configuration
export SCILOGGER="config/scilogger.ini"

# set the multiprocessing options (zero for disabling)
export PARALLEL="4"

# set the multithreading options
#    - if multiprocessing is used, multithreading should be disabled
#    - if multiprocessing is not used, multithreading can be enabled
#    - using multiprocessing and multithreading will create overcommitment
export OMP_NUM_THREADS="1"
export MKL_NUM_THREADS="1"
export BLIS_NUM_THREADS="1"
export NUMBA_NUM_THREADS="1"
export NUMEXPR_NUM_THREADS="1"
export OPENBLAS_NUM_THREADS="1"
export VECLIB_MAXIMUM_THREADS="1"
```

### Compute Single Designs

```bash
# compute a single inductor design (user-defined)
#    - "--config" - name of the inductor configuration
#    - "--shape" - tag specifying the inductor geometry
#    - "--folder" - folder for the results (to be created)
#    - "config/data_single.py" - contains the all the options

# compute a solenoid
python run_0_single.py \
    --config floating \
    --shape solenoid \
    --folder data_eval/single_solenoid 

# compute a spiral
python run_0_single.py \
    --config floating \
    --shape spiral \
    --folder data_eval/single_spiral 
```

### Dataset Generation

```bash
# create a dataset with many designs
#    - "--config" - name of the inductor configuration
#    - "--shape" - tag specifying the inductor geometry
#    - "--name" - name of the study (to be created in the SQL database)
#    - "--parallel" - number of tasks running in parallel
#    - "config/data_dataset.py" - contains the all the options

# generate random geometries (computationally intensive) 
python run_1_dataset.py \
    --config floating \
    --shape rand \
    --name rand_seed \
    --parallel $PARALLEL

# sweep solenoid inductor geometries (computationally intensive) 
python run_1_dataset.py \
    --config floating \
    --shape solenoid \
    --name array_solenoid \
    --parallel $PARALLEL

# sweep spiral inductor geometries (computationally intensive) 
python run_1_dataset.py \
    --config floating \
    --shape spiral \
    --name array_spiral \
    --parallel $PARALLEL
    
# check the database status
python run_manage.py --quiet stat
```

### Shape Optimization

```bash
# optimize inductor designs (shape optimization)
#    - "--config" - name of the inductor configuration
#    - "--solver" - name of the solver configuration
#    - "--name" - name of the study (to be created in the SQL database)
#    - "--seed" - name of study with the initial values (in the SQL database)
#    - "--parallel" - number of tasks running in parallel
#    - "config/data_optim.py" - contains the all the options

# shape optimization using PyGAD (computationally intensive) 
python run_2_optim.py \
    --config floating \
    --solver pygad \
    --name opt_pygad \
    --seed rand_seed \
    --parallel $PARALLEL

# shape optimization using Nevergrad (computationally intensive) 
python run_2_optim.py \
    --config floating \
    --solver nevergrad \
    --name opt_nevergrad \
    --seed rand_seed \
    --parallel $PARALLEL
    
# check the database status
python run_manage.py --quiet stat
```

### Dataset Extraction

```bash
# retrieve and export inductor designs
#    - "--name" - name of the study (to be retrieved from the SQL database)
#    - "--file" - filename for the dataset (to be created)
#    - "config/data_export.py" - contains the all the options

# export the solenoid designs
python run_3_export.py \
    --name array_solenoid \
    --file data_export/array_solenoid.pck

# export the spiral designs
python run_3_export.py \
    --name array_spiral \
    --file data_export/array_spiral.pck

# export the PyGAD results
python run_3_export.py \
    --name opt_pygad \
    --file data_export/opt_pygad.pck

# export the Nevergrad results
python run_3_export.py \
    --name opt_nevergrad \
    --file data_export/opt_nevergrad.pck
```

### Compute Selected Designs

```bash
# compute a single inductor design (from a dataset)
#    - "--config" - name of the inductor configuration
#    - "--extract" - tag specifying the method for extracting a design
#    - "--file" - filename for the dataset (to be loaded)
#    - "--folder" - folder for the results (to be created)
#    - "config/data_eval.py" - contains the all the options

# extract and compute a random solenoid design
python run_4_eval.py \
    --config floating \
    --extract rand \
    --file data_export/array_solenoid.pck \
    --folder data_eval/array_solenoid

# extract and compute a random spiral design
python run_4_eval.py \
    --config floating \
    --extract rand \
    --file data_export/array_spiral.pck \
    --folder data_eval/array_spiral

# extract and compute the best PyGAD design
python run_4_eval.py \
    --config floating \
    --extract best \
    --file data_export/opt_pygad.pck \
    --folder data_eval/opt_pygad

# extract and compute the best Nevergrad design
python run_4_eval.py \
    --config floating \
    --extract best \
    --file data_export/opt_nevergrad.pck \
    --folder data_eval/opt_nevergrad
```

### PEEC Plots, GERBER, and CAD

```bash
# plot the results of the 3D PEEC solver
python pypostproc/plot.py \
    --folder_in data_eval/single_solenoid \
    --folder_out data_postproc/single_solenoid \
    --cfg_viewer config/plotting/viewer.yaml \
    --cfg_plotter config/plotting/plotter.yaml
python pypostproc/plot.py \
    --folder_in data_eval/single_spiral \
    --folder_out data_postproc/single_spiral \
    --cfg_viewer config/plotting/viewer.yaml \
    --cfg_plotter config/plotting/plotter.yaml

# export the geometries to GERBER files
python pypostproc/gerber.py \
    --folder_in data_eval/single_solenoid \
    --folder_out data_postproc/single_solenoid \
    --cfg_gerber config/postproc/gerber.yaml
python pypostproc/gerber.py \
    --folder_in data_eval/single_spiral \
    --folder_out data_postproc/single_spiral \
    --cfg_gerber config/postproc/gerber.yaml

# export the geometries to CAD files
python pypostproc/cad.py \
    --folder_in data_eval/single_solenoid \
    --folder_out data_postproc/single_solenoid \
    --cfg_cad config/postproc/cad.yaml
python pypostproc/cad.py \
    --folder_in data_eval/single_spiral \
    --folder_out data_postproc/single_spiral \
    --cfg_cad config/postproc/cad.yaml
```
