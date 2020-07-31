# cmec-driver
Coordinated Model Evaluation Capabilities (CMEC) driver

This driver is used for organizing evaluation modules on the local system.

To compile:

make

After compilation, the "cmec-driver" executable will be placed into the "bin" directory.

Execution:

cmec-driver register <module dir>
- Register the CMEC-compatible module in <module dir> using either a "contents.json" or "settings.json" file.

cmec-driver unregister <module name>
- Unregister the specified module (remove it from the CMEC library file).

cmec-driver list [all]
- List all modules currently in the CMEC library.  If [all] is specified, also list all module configurations.

cmec-driver run <obs dir> <model dir> <working dir> <list of modules> ...
- Execute the specified list of modules on the provided observational data, model data, and working data.

