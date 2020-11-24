"""CMEC test cases

Generates the contents, settings, and driver files for a toy module.
Runs all the cmec-driver commands for the module.

Todo:
Test running multiple modules
Test errors - no driver files, no contents, no settings, etc
Test module with only 1 config
"""
import json
from pathlib import Path
import os

class setup_test_module():
    """Sets up a test module directory."""
    def __init__(self, module_name, module_path, config_list):
        os.system("rm " + module_path + "/*")

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
        input_path = "CMIP5.historical.ACCESS1-0.r1i1p1.AC.1981.nc"
        test_path = str(Path.home() / "Documents/git/cmec-driver/test/calculate_weighted_mean.py")
        print(test_path)
        with open(filepath, "w") as script:
            script.write("#!/bin/bash\npython " + test_path + " $CMEC_MODEL_DATA/" + input_path + " rlut $CMEC_WK_DIR/weighted_mean.json")
        os.system("chmod u+x " + str(filepath))


def test_register(module_path):
    """Register test module."""
    os.system("python ../src/cmec-driver.py register " + module_path)
    print("\nCMEC Library:")
    os.system("cat ~/.cmeclibrary")


def test_unregister(module_name):
    """Unregister test module."""
    os.system("python ../src/cmec-driver.py unregister " + module_name)


def test_list(listall=True):
    """List the registered modules."""
    if listall:
        os.system("python ../src/cmec-driver.py list -all")
    else:
        os.system("python ../src/cmec-driver.py list")


def test_run(module_name, obs=True):
    """Run the test module."""
    if Path("../output/" + module_name).exists():
        os.system("rm -r ../output/" + module_name)
    if obs:
        os.system("python ../src/cmec-driver.py run -obs ../obs ../model/test/ ../output " + module_name)
    else:
        os.system("python ../src/cmec-driver.py run ../model/test/ ../output " + module_name)


if __name__ == "__main__":
    module_path = "/Users/ordonez4/Documents/test_module"
    module_name = "CMECTEST"
    config_list = ["test1"]
    # If there is only one configuration, config name will be module name
    if len(config_list) < 2:
        config_list = [module_name]
    print(config_list)
    setup_test_module(module_name, module_path, config_list)

    print("\n\n********************")
    print("Register test module")
    print("********************\n\n")
    test_register(module_path)

    print("\n\n************")
    print("List modules")
    print("************\n\n")
    test_list(listall=False)

    print("\n\n***************")
    print("Run test module")
    print("***************\n\n")
    test_run(module_name, obs=True)
    print("\nModule output file:")
    if len(config_list) == 1:
        os.system("cat ../output/" + module_name + "/weighted_mean.json")
    else:
        os.system("cat ../output/" + module_name + "/" + config_list[0] + "/weighted_mean.json")

    print("\n\n**********************")
    print("Unregister test module")
    print("**********************\n\n")
    test_unregister(module_name)
    print("\n\n")

