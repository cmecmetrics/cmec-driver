"""CMEC test cases

Generates the contents, settings, data, and driver files for a fake module.
Runs the cmec-driver commands for the fake module to check basic
functionality.

The fake module calls on calculate_weighted_mean.py to do a small
calculation.

Todo:
Test errors - no driver files, no contents, no settings, etc
"""
import json
import numpy as np
from pathlib import Path
import os
import xarray as xr

class setup_test_module():
    """Sets up a test module directory.

    Args:
        module_name (str): Name of CMEC module
        module_path (str): path to module directory
        config_list (list of str): list of configurations to make
    """
    def __init__(self, module_name, module_path, config_list):
        os.system("rm " + module_path + "/*")

        Path(module_path).mkdir(exist_ok=True, parents=True)

        multiple_configs = False
        if len(config_list) > 1:
            multiple_configs = True
        self.make_contents(module_name, module_path, config_list)

        for config in config_list:
            self.make_settings(module_path, config, multiple_configs)
            self.make_driver(module_path, config)

    def make_settings(self, module_path, config, multiple_configs=False):
        """Create a settings file."""
        settings = {"info": "", "obslist": {}, "settings": {}, "varlist": {}}
        settings["info"] = "Settings used for CMEC test module"
        settings["settings"]["async"] = "none"
        settings["settings"]["description"] = "Calculate metrics for a small test case"
        settings["settings"]["driver"] = config + "_driver.sh"
        settings["settings"]["name"] = config
        settings["settings"]["long_name"] = "CMEC test case " + config

        if multiple_configs:
            filepath = Path(module_path) / (config + "_settings.json")
        else:
            settings["module"] = {}
            settings["module"]["name"] = config
            filepath = Path(module_path) / "settings.json"

        with open(filepath, "w") as outfile:
            json.dump(settings, outfile, indent=4)

    def make_contents(self, module_name, module_path, config_list):
        """Create a contents file."""
        contents = {"module": {}, "contents": ""}
        contents["module"]["name"] = module_name
        contents["module"]["long_name"] = "CMEC test module"
        contents["module"]["version"] = "v20201117"
        if len(config_list) > 1:
            contents["contents"] = [(config + "_settings.json") for config in config_list]
        else:
            contents["contents"] = ["settings.json"]

        filepath = Path(module_path) / "contents.json"

        with open(filepath, "w") as outfile:
            json.dump(contents, outfile, indent=4)

    def make_driver(self, module_path, config):
        """Create driver file."""
        filepath = Path(module_path) / (config + "_driver.sh")
        input_path = "model_data.nc"
        self.make_model_data(input_path)
        test_path = str("./calculate_weighted_mean.py")
        with open(filepath, "w") as script:
            script.write(
                "#!/bin/bash\npython " + test_path
                + " $CMEC_MODEL_DATA/" + input_path
                + " rlut $CMEC_WK_DIR/weighted_mean.json")
        os.system("chmod u+x " + str(filepath))

    def make_model_data(self, input_path):
        """Create fake model data if it does not already exist."""
        model_path = Path("./model/")
        data_path = model_path / input_path
        if not model_path.exists():
            model_path.mkdir(parents=True)
        if not data_path.exists():
            lat = np.linspace(-90,90,180)
            lon = np.linspace(0,360,360,endpoint=False)
            time = np.linspace(0,2,2)
            coordinates = {'lat':lat,'lon':lon,'time':time}
            rand_data = np.ones((180, 360, 2))
            new_array = xr.Dataset(
                data_vars=dict(rlut=(['lat','lon','time'], rand_data)),
                coords=coordinates,attrs=dict(description="fake data for test"))
            new_array.to_netcdf(str(data_path), mode="w")

def setup_directories():
    model_path = Path("./model")
    obs_path = Path("./obs")
    out_path = Path("./output")
    model_path.mkdir(exist_ok=True)
    obs_path.mkdir(exist_ok=True)
    out_path.mkdir(exist_ok=True)

def test_register(module_path):
    """Register test module."""
    os.system("python ../cmec-driver.py register " + module_path)
    print("\nCMEC Library:")
    os.system("cat ~/.cmeclibrary")
    print("\nCMEC config:")
    os.system("cat ../config/cmec.json")

def test_unregister(module_name):
    """Unregister test module."""
    os.system("python ../cmec-driver.py unregister " + module_name)

def test_list(listall=True):
    """List the registered modules."""
    if listall:
        os.system("python ../cmec-driver.py list -all")
    else:
        os.system("python ../cmec-driver.py list")

def test_run(module_name, obs=True):
    """Run the test module."""
    if Path("../output/" + module_name).exists():
        os.system("rm -r ../output/" + module_name)
    if obs:
        os.system("python ../cmec-driver.py run -obs obs model output " + module_name)
    else:
        os.system("python ../cmec-driver.py run model output " + module_name)


if __name__ == "__main__":
    # Make sure needed directories exist
    setup_directories()

    # Set up two fake modules
    # If there is only one configuration, config name must be module name
    module_path_1 = "./test_module"
    module_name_1 = "CMECTEST_1"
    config_list_1 = ["CMECTEST_1"]
    setup_test_module(module_name_1, module_path_1, config_list_1)

    module_path_2 = "./test_module_2"
    module_name_2 = "CMECTEST_2"
    config_list_2 = ["test2", "test3"]
    setup_test_module(module_name_2, module_path_2, config_list_2)

    # Test the 4 cmec-driver commands
    print("\n\n********************")
    print("Register test module")
    print("********************\n\n")
    test_register(module_path_1)
    test_register(module_path_2)

    print("\n\n************")
    print("List modules")
    print("************\n\n")
    test_list(listall=False)

    print("\n\n***************")
    print("Run test module")
    print("***************\n\n")
    # Test just one module
    test_run(module_name_1)
    # Test running two modules at once
    module_run = module_name_1 + " " + module_name_2
    test_run(module_run, obs=True)
    print("\nModule output file:")
    if len(config_list_1) == 1:
        os.system("cat output/" + module_name_1 + "/weighted_mean.json")
    else:
        os.system("cat output/" + module_name_1 + "/" + config_list_1[0] + "/weighted_mean.json")

    print("\n\n**********************")
    print("Unregister test module")
    print("**********************\n\n")
    test_unregister(module_name_1)
    test_unregister(module_name_2)
    print("\n\n")

