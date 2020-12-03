# CMEC test script

This script uses the python cmec-driver to run the register, list, run, and unregister commands for a fake module with fake data. It is a quick way to validate the basic functionality of cmec-driver.py.

## Before running:
The test module assumes it is being run from within the cmec-driver/test directory. This script depends on numpy and xarray along with other modules from the Python standard library.

Make any desired changes to the fake modules in the cmec-test.py "main" method and save.

## To run:
`python cmec-test.py`

## Outputs
The script will create a model, obs, and output folder, along with folders for each of the test modules. Check cmec-driver/test/output/[fake module name] for test metric outputs.


