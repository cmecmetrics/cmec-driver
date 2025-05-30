[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.15548747.svg)](https://doi.org/10.5281/zenodo.15548747)

# cmec-driver
Coordinated Model Evaluation Capabilities (CMEC) driver

This driver is used for organizing evaluation modules on the local system.

## Environment
The driver only requires packages from the Python 3 standard library. The test module (test/cmec-test.py) requires numpy and xarray.

## Installation
It is recommended that you create a new Python 3 environment to install the driver. After creating and activating this environment, there are three ways to obtain the cmec-driver package:

1. Use conda to install the latest release:  
`conda install -c conda-forge cmec_driver`  
  
2. Clone this repository to use the latest dev version. Enter the cmec-driver directory and do:
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
More detailed installation and set up instructions (including module-specific instructions) can be found in the [wiki](https://github.com/cmecmetrics/cmec-driver/wiki). 

**Find an issue?**  
If you find a bug or run into a problem, please open a new Issue.  

## License  
CMEC driver is distributed under the terms of the BSD 3-Clause License.  
LLNL-CODE-847758

## Acknowledgement
Content in this repository is developed by climate and computer scientists from the Program for Climate Model Diagnosis and Intercomparison ([PCMDI][PCMDI]) at Lawrence Livermore National Laboratory ([LLNL][LLNL]). This work is sponsored by the Regional and Global Model Analysis ([RGMA][RGMA]) program, of the Earth and Environmental Systems Sciences Division ([EESSD][EESSD]) in the Office of Biological and Environmental Research ([BER][BER]) within the [Department of Energy][DOE]'s [Office of Science][OS]. The work is performed under the auspices of the U.S. Department of Energy by Lawrence Livermore National Laboratory under Contract DE-AC52-07NA27344.  

[PCMDI]: https://pcmdi.llnl.gov/
[LLNL]: https://www.llnl.gov/
[RGMA]: https://climatemodeling.science.energy.gov/program/regional-global-model-analysis
[EESSD]: https://science.osti.gov/ber/Research/eessd
[BER]: https://science.osti.gov/ber
[DOE]: https://www.energy.gov/
[OS]: https://science.osti.gov/


<p>
    <img src="https://github.com/PCMDI/assets/blob/main/DOE/480px-DOE_Seal_Color.png?raw=true"
         width="65"
         style="margin-right: 30px"
         title="United States Department of Energy"
         alt="United States Department of Energy"
    >&nbsp;
    <img src="https://github.com/PCMDI/assets/blob/main/LLNL/212px-LLNLiconPMS286-WHITEBACKGROUND.png?raw=true"
         width="65"
         title="Lawrence Livermore National Laboratory"
         alt="Lawrence Livermore National Laboratory"
    >
</p>
