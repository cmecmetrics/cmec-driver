# cmec-driver
Coordinated Model Evaluation Capabilities (CMEC) driver

This driver is used for organizing evaluation modules on the local system.

## Environment
The driver only requires packages from the Python 3 standard library. The test module (test/cmec-test.py) requires numpy and xarray.

## Installation
It is recommended that you create a new Python 3 environment to install the driver. After creating and activating this environment, there are three ways to obtain the cmec-driver package:

1. Use conda to install the package:  
`conda install -c conda-forge cmec_driver`  
  
2. Clone this repository. Enter the cmec-driver directory and do:
`pip install ./`
  
3. Download the most recent release of cmec-driver from github. Extract the source code, enter the cmec-driver directory, and do:  
`pip install ./`

After `cmec-driver register` is run for the first time, two hidden files will be created in your home directory (.cmeclibrary and .cmec/cmec.json).

## Test
A test script is provided in the "/test" directory along with instructions in the test README.

## Usage:
The command line syntax is slightly different from past versions of cmec-driver. Flags have been updated to use two hyphens, and once the driver is installed you do not need to call "python" before running.

**Setup**  
Add or remove conda package information in cmec library.  
`cmec-driver setup --conda_source <path to conda executable> --env_root <conda env directory> --clear_conda`  
Example:   
`cmec-driver setup --conda_source ~/miniconda/etc/profile.d/conda.sh --env_root ~/miniconda/envs`  

**Register**  
Add a module to the cmec library.  
`cmec-driver register <module dir>`  
Example:   
`cmec-driver register ../ILAMB`  

**Unregister**  
Remove a module from the cmec library.  
`cmec-driver unregister <module name>`  
Example:   
`cmec-driver unregister ILAMB`  

**List** 
List all the registered modules.   
`cmec-driver list (--all)`  

**Run**  
Run one or more metrics modules.  
`cmec-driver run --obs <obs dir> <model dir> <working dir> <list of modules>`  
Example:   
`cmec-driver run --obs obs/ model/ output/ ILAMB/Sample`  
- The --obs directory is optional but other directories are required.

**Runtime Settings**  
Some modules allow settings to be modified. These settings can be changed in ~/.cmec/cmec.json after the module is registered.

**Further instructions**  
More detailed installation and set up instructions (including module-specific instructions) can be found in the [wiki](https://github.com/cmecmetrics/cmec-driver/wiki/Installation-and-Setup).

**Find an issue?**
If you find a bug or run into a problem, please open a new Issue.  
