# cmec-driver
Coordinated Model Evaluation Capabilities (CMEC) driver

This driver is used for organizing evaluation modules on the local system.

To compile:

make

After compilation, the "cmec-driver" executable will be placed into the "bin" directory.

Execution:

cmec-driver register \<module dir\>
- Register the CMEC-compatible module in \<module dir\> using either a "contents.json" or "settings.json" file.

cmec-driver unregister \<module name\>
- Unregister the specified module (remove it from the CMEC library file).

cmec-driver list [all]
- List all modules currently in the CMEC library.  If [all] is specified, also list all module configurations.

cmec-driver run \<obs dir\> \<model dir\> \<working dir\> \<list of modules\> ...
- Execute the specified list of modules on the provided observational data, model data, and working data.

## cmec-driver python
A python version of the driver is available. The driver only requires packages from the python standard library. The test module (test/cmec-test.py) requires numpy and xarray.

Usage is similar to the original C++ cmec-driver. From the cmec-driver directory:

python cmec-driver.py setup -conda_source \<path to conda executable\> -env_root \<conda env directory\> -clear_conda

python cmec-driver.py register \<module dir\>

python cmec-driver.py unregister \<module name\>

python cmec-driver.py list (-all)

python cmec-driver.py run -obs \<obs dir\> \<model dir\> \<working dir\> \<list of modules\>
- The -obs directory is optional but other directories are required.

Some modules allow settings to be modified. These settings can be changed in config/cmec.json after the module is registered.

More detailed installation and set up instructions can be found in the [wiki](https://github.com/cmecmetrics/cmec-driver/wiki/Installation-and-Setup).
