# cmec-driver
Coordinated Model Evaluation Capabilities (CMEC) driver

This driver is used for organizing evaluation modules on the local system.

## Environment
The driver only requires packages from the Python 3 standard library. The test module (test/cmec-test.py) requires numpy and xarray.

## Installation
It is recommended that you create a new Python 3 environment to install the driver. Activate this environment, and from the cmec-driver directory do:
`python setup.py install`

After `cmec-driver register` is run for the first time, two hidden files will be created in your home directory (.cmeclibrary and .cmec/cmec.json).

## Test
A test script is provided in the "/test" directory along with instructions in the test README.

## Usage:
The command line syntax is slightly different from past versions of cmec-driver. Flags have been updated to use two hyphens, and once the driver is installed you do not need to call "python" before running.

*Setup*  
Add or remove conda package information in cmec library.  
`cmec-driver setup --conda_source <path to conda executable> --env_root <conda env directory> --clear_conda`  
`cmec-driver setup --conda_source ~/miniconda/etc/profile.d/conda.sh --env_root ~/miniconda/envs`  

*Register*  
Add a module to the cmec library.  
`cmec-driver register <module dir>`  
`cmec-driver register ../ILAMB`  

*Unregister*  
Remove a module from the cmec library.  
`cmec-driver unregister <module name>`  
`cmec-driver unregister ILAMB`  

*List* 
List all the registered modules.   
`cmec-driver list (--all)`  

*Run*  
Run one or more metrics modules.  
`cmec-driver run --obs <obs dir> <model dir> <working dir> <list of modules>`  
`cmec-driver run --obs obs/ model/ output/ ILAMB/Sample`  
- The --obs directory is optional but other directories are required.

Some modules allow settings to be modified. These settings can be changed in ~/.cmec/cmec.json after the module is registered.

More detailed installation and set up instructions can be found in the [wiki](https://github.com/cmecmetrics/cmec-driver/wiki/Installation-and-Setup).
