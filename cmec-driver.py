"""
CMEC driver

Interface for running CMEC-compliant modules.

Examples:
    Registering a module::

    $ python cmec_driver.py register <module_directory_path>
    $ python cmec_driver.py register ~/modules/ILAMB

    Unregistering a module::

    $ python cmec_driver.py unregister <module_name>
    $ python cmec_driver.py unregister ILAMB

    List modules::

    $ python cmec_driver.py list -all

    Run a module::

    $ python cmec_driver.py run -obs <observations_folder> <model_folder> <output_folder> <module_name>
    $ python cmec_driver.py run -obs ./obs ./model ./output PMP/meanclimate

Attributes:
    version (str): CMEC driver version
    cmec_library_name (str): standard file name for cmec library
    cmec_toc_name (str): standard file name for module contents
    cmec_settings_name (str): standard file name for module settings

Todo:
Add tests
"""
from pathlib import Path
import json
import string
import sys
import os

version = "20200731"
cmec_library_name = ".cmeclibrary"
cmec_toc_name = "contents.json"
cmec_settings_name = "settings.json"


def user_prompt(question, default = "yes"):
    """Asks the user a yes/no question

    Args:
        question (str): Question for the user
    """
    prompt = '[y/n] '
    valid = {"yes": True, "y": True, "no": False, "n": False}

    while True:
        sys.stdout.write(question + " " + prompt)
        choice = input().lower()
        if choice == '':
            return valid[default]
        if choice in valid:
            return valid[choice]
    sys.stdout.write("Please respond 'y' or 'n' ")


class CMECError(Exception):
    """Errors related to CMEC standards.

    Args:
        message (str): Explanation of the error
    """
    def __init__(self, message):
        super(CMECError, self).__init__(message)
        self.message = message


class CMECLibrary():
    """Interact with the CMEC library.

    The CMEC library file (~/.cmeclibrary) is, most simply, a json
    containing the keys "modules", "cmec-driver", and "version". This
    class can initialize a new library, read from the library, and edit
    the library.
    """
    def __init__(self):
        self.path=""
        self.map_module_path_list = {}
        self.jlib = {"modules": {}, "cmec-driver": {}, "version": version}

    def Clear(self):
        self.path = ""
        self.map_module_path_list = {}
        self.jlib = {"modules": {}, "cmec-driver": {}, "version": version}

    def InitializePath(self):
        """Get the path for the .cmeclibrary file"""
        homedir = Path.home()

        if homedir.exists():
            self.path = homedir / cmec_library_name

    def Read(self):
        """Load the contents of the CMEC library.

        Loads the .cmeclibrary file as a json and checks that the
        contents and formatting match CMEC standards.
        """
        # Clear the library
        self.Clear()

        # Initialize path
        self.InitializePath()

        # Load the library
        if not self.path.exists():
            print("CMEC library not found; creating new library")

            # Create library if not found
            with open(self.path, "w") as outfile:
                json.dump(self.jlib, outfile)

        # Load and check contents against standards
        with open(self.path, "r") as jsonfile:
            self.jlib = json.load(jsonfile)

        for key in ["cmec-driver", "version", "modules"]:
            if key not in self.jlib:
                raise CMECError(
                    "Malformed CMEC library file missing key " + key)

            if not isinstance(key, str):
                raise CMECError(
                    "Malformed CMEC library file: "
                    + key + " is not of type string")

        for key in self.jlib["modules"]:
            if not isinstance(self.jlib["modules"][key], str):
                raise CMECError(
                    "Malformed CMEC library file: an entry of the 'modules'"
                    + " array is not of type string")

            if key in self.map_module_path_list:
                raise CMECError(
                    "Malformed CMEC library file: Repeated module name " + key)

            self.map_module_path_list[key] = Path(self.jlib["modules"][key])

    def Write(self):
        self.InitializePath()

        with open(self.path, "w") as outfile:
            json.dump(self.jlib, outfile)

    def Insert(self,module_name, filepath):
        """Add a module to the library

        Args:
            module_name (str): name of module
            filepath (str or Path): path to the module directory
        """
        # Check if module already exists:
        if module_name in self.map_module_path_list:
            raise CMECError("Module already exists in library; if path has changed first run 'unregister'")

        if not isinstance(filepath, Path):
            if not isinstance(filepath, str):
                raise CMECError("Malformed path is not of type string or pathlib.Path")
            filepath = Path(filepath)

        # Insert module
        self.map_module_path_list[module_name] = filepath
        self.jlib["modules"][module_name] = str(filepath)

    def Remove(self,module_name):
        if module_name not in self.map_module_path_list:
            raise CMECError("Module " + module_name + " not found in library")

        if module_name not in self.jlib["modules"]:
            raise CMECError("Module appears in map but not in json representation")

        # Remove from map and json
        self.map_module_path_list.pop(module_name)
        self.jlib["modules"].pop(module_name)

    def size(self):
        """Get the number of modules in the library"""
        return len(self.map_module_path_list)

    def find(self, strModule):
        """Get the path to a specific module"""
        if strModule in self.map_module_path_list:
            return self.map_module_path_list[strModule]
        return False

    def getModuleList(self):
        """Get a list of the modules in the library"""
        return [*self.map_module_path_list]


class CMECModuleSettings():
    """Interface with module settings file"""
    def __init__(self):
        self.path = ""
        self.jsettings = {}

    def ExistsInmodule_path(self, filepath):
        """Check if a settings file exists for a module.

        Returns True if settings.json found in path, otherwise False.

        Args:
            filepath (str or Path): path for the module directory
        """
        if not isinstance(filepath, Path):
            filepath = Path(filepath)

        path_settings = filepath / cmec_settings_name

        return path_settings.exists()

    def Clear(self):
        self.path = ""
        self.jsettings = {}

    def ReadFromFile(self, path_settings):
        """Read the CMEC module contents file.

        Loads the contents file as a json and checks that the contents
        match CMEC standards.
        """
        self.Clear()

        if not isinstance(path_settings, Path):
            path_settings = Path(path_settings)

        self.path = path_settings

        with open(self.path, "r") as cmec_json:
            self.jsettings = json.load(cmec_json)

        for key in ["settings", "obslist"]:
            if key not in self.jsettings:
                raise CMECError(
                    "Malformed CMEC settings file "
                    + str(path_settings) + ": missing key " + key)

        for key in ["name", "long_name", "driver"]:
            if key not in self.jsettings["settings"]:
                raise CMECError(
                    "Malformed CMEC settings file "
                    + str(path_settings) + ": missing key settings:" + key)
                # also check type

    def CreateConfig(self, config_file, module_name=''):
        """Adds module specific user settings to cmec config yaml"""
        config_name = self.GetName()
        if module_name != '':
            config_name = module_name + '/' + config_name

        # grab default user settings from module
        module_settings = {}
        if 'default_parameters' in self.jsettings:
            module_config = self.jsettings['default_parameters']
            module_settings.update({config_name: module_config})
        else:
            module_settings.update({config_name: {}})

        # load existing cmec config or create new config
        if config_file.exists():
            with open(config_file, "r") as cfile:
                all_settings = json.load(cfile)
            # check that config isn't empty
            if isinstance(all_settings, dict):
                all_settings.update(module_settings)
            else:
                all_settings = module_settings
        else:
            # create config if it doesn't exist
            all_settings = module_settings
            config_file.mkdir(parents=True)
        with open(config_file, "w") as cfile:
            json.dump(all_settings, cfile, indent=4)

    def RemoveConfig(self, config_file, module_name=''):
        config_name = self.GetName()
        if module_name != '':
            config_name = module_name + '/' + config_name
        if config_file.exists():
            with open(config_file,"r") as cfile:
                all_settings = json.load(cfile)
                if isinstance(all_settings, dict):
                    all_settings.pop(config_name, None)
            with open(config_file, "w") as cfile:
                json.dump(all_settings, cfile, indent=4)

    def GetName(self):
        """Returns the module name."""
        return self.jsettings["settings"]["name"]

    def GetLongName(self):
        """Returns module long name."""
        return self.jsettings["settings"]["long_name"]

    def GetDriverScript(self):
        """Returns driver file name."""
        return self.jsettings["settings"]["driver"]


class CMECModuleTOC():
    """Interface with module contents file."""
    def __init__(self):
        self.path = ""
        self.map_configs = {}
        self.jcmec = {}
        self.jcontents = {}

    def ExistsInmodule_path(self, path_module):
        """Check if contents file exists for module

        Returns True if contents.json found in module directory.
        Otherwise, returns False.

        Args:
            path_module (str or Path): path to module directory
        """
        if not isinstance(path_module, Path):
            path_module = Path(path_module)

        path_settings = path_module / cmec_toc_name

        return path_settings.exists()

    def Clear(self):
        self.path = ""
        self.map_configs = {}
        self.jcmec = {}
        self.jcontents = {}

    def ReadFrommodule_path(self, path_module):
        """Read the CMEC module contents file

        Loads the contents.json for the specified module and
        checks that the json matches the CMEC standards.

        Args:
            path_module (str or Path): path to the module directory
        """
        # Clear and get path
        self.Clear()

        if not isinstance(path_module, Path):
            path_module = Path(path_module)

        self.path = path_module / cmec_toc_name

        # Parse and validate CMEC json
        with open(self.path, "r") as cmec_toc:
            self.jcmec = json.load(cmec_toc)

        for key in ["module", "contents"]:
            if key not in self.jcmec:
                raise CMECError(
                    "Malformed CMEC library file "
                    + self.path + ": missing key " + key)

        for key in ["name", "long_name"]:
            if key not in self.jcmec["module"]:
                raise CMECError(
                    "Malformed CMEC library file "
                    + self.path + ": missing key module:" + key)

        if isinstance(self.jcmec["contents"], list):
            self.jcontents = self.jcmec["contents"]
        else:
            print("Malformed CMEC library file:'contents' is not of type list")

        for item in self.jcontents:
            if isinstance(item, str):
                cmec_settings = CMECModuleSettings()
                path_settings = path_module / item
                cmec_settings.ReadFromFile(path_settings)
                self.map_configs[cmec_settings.GetName()] = path_settings

            else:
                print(
                    "Malformed CMEC Library file: an entry of the"
                    + "'contents' array is not of type string")

    def Insert(self, config_name, filepath):
        """Add a configuration

        Args:
            config_name (str): name of configuration
            filepath (str or Path): path to the configuration file
        """
        # Check if config already exists
        if config_name in self.map_configs:
            print("Repeated configuration name " + config_name)
            return

        if not isinstance(filepath, Path):
            filepath = Path(filepath)

        # Insert module
        self.map_configs[config_name] = filepath

        self.jcmec["contents"][config_name] = str(filepath)

    def CreateConfig(self, config_file, path_module):
        """create module settings yaml for each configuration"""
        for item in self.jcontents:
            if isinstance(item, str):
                cmec_settings = CMECModuleSettings()
                path_settings = path_module / item
                cmec_settings.ReadFromFile(path_settings)
                cmec_settings.CreateConfig(config_file, self.getName())

    def RemoveConfig(self, config_file, path_module):
        for item in self.jcontents:
            if isinstance(item, str):
                cmec_settings = CMECModuleSettings()
                path_settings = path_module/item
                cmec_settings.ReadFromFile(path_settings)
                cmec_settings.RemoveConfig(config_file, self.getName())

    def getName(self):
        """Return the name of the module"""
        return self.jcmec["module"]["name"]

    def getLongName(self):
        """Return the long name of the module"""
        return self.jcmec["module"]["long_name"]

    def size(self):
        """Return the number of configs"""
        return len(self.map_configs)

    def configList(self):
        """Return the list of configs"""
        return [*self.map_configs]

    def find(self, setting):
        """Return the setting file path"""
        if setting in self.map_configs:
            return self.map_configs[setting]
        return False


def cmec_register(module_dir, config_file):
    """Add a module to the cmec library.

    Args:
        module_dir (str or Path): path to the module directory
    """
    print(module_dir)
    if not isinstance(module_dir, Path):
        module_dir = Path(module_dir)

    print("Registering " + str(module_dir))

    cmec_settings = CMECModuleSettings()
    cmec_toc = CMECModuleTOC()

    # check if module contains a settings file
    if cmec_settings.ExistsInmodule_path(module_dir):
        print("Validating " + cmec_settings_name)
        cmec_settings.ReadFromFile(module_dir / cmec_settings_name)
        str_name = cmec_settings.GetName()
        cmec_settings.CreateConfig(config_file)

    # or check if module contains a contents file
    elif cmec_toc.ExistsInmodule_path(module_dir):
        print("Validating " + cmec_toc_name)

        cmec_toc.ReadFrommodule_path(module_dir)
        cmec_toc.CreateConfig(config_file, module_dir)

        str_name = cmec_toc.getName()
        str_long_name = cmec_toc.getLongName()

        print("Module " + str_name + " " + str_long_name)
        print("Contains " + str(cmec_toc.size()) + " configurations")
        print("------------------------------------------------------------")
        for item in cmec_toc.configList():
            print(str_name + "/" + item)
        print("------------------------------------------------------------")

    else:
        raise CMECError(
            "Module path must contain "
            + cmec_toc_name + " or " + cmec_settings_name)

    # Add to CMEC library
    print("Reading CMEC library")
    lib = CMECLibrary()
    lib.Read()

    print("Adding new module to library")
    lib.Insert(str_name, module_dir)

    print("Writing CMEC library")
    lib.Write()


def cmec_unregister(module_name, config_file):
    """Remove a module from the cmec library.

    Args:
        module_name (str): name of module to remove
    """
    print("Reading the CMEC library")
    lib = CMECLibrary()
    lib.Read()

    print("Removing configuration")
    module_dir = lib.find(module_name)
    cmec_settings = CMECModuleSettings()
    cmec_toc = CMECModuleTOC()
    if cmec_settings.ExistsInmodule_path(module_dir):
        cmec_settings.ReadFromFile(module_dir / cmec_settings_name)
        cmec_settings.RemoveConfig(config_file)
    elif cmec_toc.ExistsInmodule_path(module_dir):
        cmec_toc.ReadFrommodule_path(module_dir)
        cmec_toc.RemoveConfig(config_file, module_dir)

    print("Removing module")
    lib.Remove(module_name)

    print("Writing CMEC library")
    lib.Write()

def cmec_list(listAll):
    """List modules in cmec library.

    Args:
        listAll (bool): if True, list configurations
    """
    print("Reading CMEC library")
    lib = CMECLibrary()
    lib.Read()

    # Check for size zero library
    if lib.size() == 0:
        raise CMECError("CMEC library contains no modules")

    cmec_toc = CMECModuleTOC()

    # List modules
    print("CMEC library contains " + str(lib.size()) + " modules")
    print("------------------------------------------------------------")
    for module in lib.getModuleList():
        module_dir = lib.find(module)
        if cmec_toc.ExistsInmodule_path(module_dir):
            cmec_toc.ReadFrommodule_path(module_dir)
            print(
                " " + module + " [" + str(cmec_toc.size())
                + " configurations]" )

            if listAll:
                for config in cmec_toc.configList():
                    print("    " + module + "/" + config)
        else:
            print(" " + module + " [1 configuration]")
    print("------------------------------------------------------------")


def cmec_run(strModelDir, strWorkingDir, module_list, config_dir, strObsDir=""):
    """Run a module from the cmec library.

    Args:
        strObsDir (str or Path): path to observation directory
        strModelDir (str or Path): path to model directory
        strWorkingDir (str or Path): path to output directory
        module_list (list of strings): List of the module names to run

    Todo:
    Handle case with no observations
    Wrap text printed to cmec_run.bash
    """

    # Verify existence of each directory
    dir_list = {"Model": strModelDir, "Working": strWorkingDir}
    if strObsDir != "":
        dir_list.update({"Observations": strObsDir})

    for key in dir_list:
        if isinstance(dir_list.get(key),str) and len(dir_list[key]) == 0:
            raise CMECError(key + " data path not specified")

        tmpdir = dir_list.get(key)
        if isinstance(tmpdir, str):
            tmpdir = Path(tmpdir)
        if tmpdir.absolute().is_dir():
            dir_list[key] = tmpdir.absolute()
        else:
            raise CMECError(
                str(tmpdir.absolute())
                + " does not exist or is not a directory")

    obspath = dir_list.get("Observations")
    modpath = dir_list.get("Model")
    workpath = dir_list.get("Working")

    # Load the CMEC library
    print("Reading CMEC library")
    lib = CMECLibrary()
    lib.Read()

    # Build dirver script list
    print("Identifying drivers")

    module_path_list = []
    driver_script_list = []
    working_dir_list = []

    for module in module_list:
        # Get name of base module
        for char in module.lower():
            if char not in string.ascii_lowercase + string.digits + "_" + "/":
                raise CMECError(
                    "Non-alphanumeric characters found in module name "
                    + module)

        str_parent_module = module
        str_configuration = ""
        if "/" in module:
            str_parent_module, str_configuration = module.split("/")

        # Check for base module in library
        module_path = lib.find(str_parent_module)
        if not module_path:
            raise CMECError(
                "Module " + str_parent_module
                + " not found in CMEC library")

        # Check if module contains a settings file
        cmec_settings = CMECModuleSettings()
        cmec_toc = CMECModuleTOC()

        if cmec_settings.ExistsInmodule_path(module_path):
            if str_configuration != "":
                raise CMECError(
                    "Module " + str_parent_module
                    + " only contains a single configration")

            cmec_settings.ReadFromFile(module_path / cmec_settings_name)
            module_path_list.append(module_path)
            driver_script_list.append(module_path / cmec_settings.GetDriverScript())
            working_dir_list.append(Path(cmec_settings.GetName()))

        # Check if module contains a contents file
        elif cmec_toc.ExistsInmodule_path(module_path):
            cmec_toc.ReadFrommodule_path(module_path)
            settings = cmec_toc.configList()
            config_found = False

            for setting in settings:
                if str_configuration in ("", setting):
                    setting_path = cmec_toc.find(setting)
                    cmec_settings.ReadFromFile(setting_path)
                    module_path_list.append(setting_path)
                    driver_script_list.append(module_path / cmec_settings.GetDriverScript())
                    working_dir_list.append(Path(cmec_toc.getName()) / Path(cmec_settings.GetName()))
                    config_found = True

            if ((str_configuration != "") and not config_found):
                raise CMECError(
                    "Module " + str_parent_module
                    + " does not contain configuration " + str_configuration)
        else:
            raise CMECError(
                "Module " + str_parent_module
                + " with path " + str(module_path)
                + " does not contain " + cmec_settings_name
                + " or " + cmec_toc_name)

    assert len(module_path_list) == len(driver_script_list)
    assert len(module_path_list) == len(working_dir_list)

    # Check for zero drivers
    if not driver_script_list:
        raise CMECError("No driver files found")

    # Output driver file list
    print(
        "The following " + str(len(driver_script_list))
        + " modules will be executed:")
    print("------------------------------------------------------------")
    for working_dir, path, driver in zip(working_dir_list, module_list, driver_script_list):
        print("MODULE_NAME: " + str(working_dir))
        print("MODULE_PATH: " + str(path))
        print("  " + str(driver))
    print("------------------------------------------------------------")

    # Environment variables
    print("The following environment variables will be set:")
    print("------------------------------------------------------------")
    print("CMEC_OBS_DATA=" + str(obspath))
    print("CMEC_MODEL_DATA=" + str(modpath))
    print("CMEC_WK_DIR=" + str(workpath) + "/$MODULE_NAME")
    print("CMEC_CODE_DIR=$MODULE_PATH")
    print("CMEC_CONFIG_DIR=" + str(config_dir))
    print("------------------------------------------------------------")

    # Create output directories
    print("Creating output directories")

    for driver, working_dir in zip(driver_script_list, working_dir_list):
        path_out = workpath / working_dir

        # Check for existence of output directories
        if path_out.exists():
            question = "Path " + str(path_out) + " already exists. Overwrite?"
            overwrite = user_prompt(question, default="yes")
            if overwrite:
                os_command = "rm -rf " + str(path_out)
                os.system(os_command)
                # Check exit code?
            else:
                raise CMECError("Unable to clear output directory")

        # Create directories
        path_out.mkdir(parents=True)

    # Create command scripts
    env_scripts = []
    for driver, workingDir, mPath in zip(driver_script_list, working_dir_list, module_path_list):
        path_working_dir = workpath / workingDir
        path_script = path_working_dir / "cmec_run.bash"
        env_scripts.append(path_script)
        print(str(path_script))
        with open(path_script, "w") as script:
            script.write("#!/bin/bash\nexport CMEC_CODE_DIR=%s\nexport CMEC_OBS_DATA=%s\nexport CMEC_MODEL_DATA=%s\nexport CMEC_WK_DIR=%s\nexport CMEC_CONFIG_DIR=%s\n%s" % (module_path, obspath, modpath, path_working_dir, config_dir, driver))
        os.system("chmod u+x " + str(path_script))

    # Execute command scripts
    print("Executing driver scripts")
    for env_script, work_dir in zip(env_scripts, working_dir_list):
        print("------------------------------------------------------------")
        print(str(work_dir))
        os.system(str(env_script))
    print("------------------------------------------------------------")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Process command line cmec-driver input")
    # Create subparsers for register, unregister, list, and run commands
    subparsers = parser.add_subparsers(
        help="commands are 'register', 'unregister', 'run', 'list'",
        dest="command")
    parser_reg = subparsers.add_parser(
        "register", help="add module to cmec library")
    parser_unreg = subparsers.add_parser(
        "unregister", help="remove module from cmec library")
    parser_list = subparsers.add_parser(
        "list", help="list modules in cmec library")
    parser_run = subparsers.add_parser(
        "run", help="run chosen modules")

    parser_reg.add_argument("modpath", type=str)
    parser_unreg.add_argument("module")
    parser_list.add_argument("-all", action="store_true",default=False,
        help="list modules and configurations")
    parser_run.add_argument("-obs", default="", help="observations directory")
    parser_run.add_argument("model", help="model directory")
    parser_run.add_argument("output", help="output directory")
    parser_run.add_argument("module", nargs="+", help="module names")

    # get the rest of the arguments
    args = parser.parse_args()

    # cmec config goes in cmec-driver/config folder
    config_file = Path(__file__).absolute().parents[0] / Path("config/cmec.json")

    # Register
    if args.command == "register":
        if args.modpath:
            cmec_register(args.modpath, config_file)
        else:
            print("Usage: python cmec-driver.py register <mod dir>")

    # Unregister
    if args.command == "unregister":
        if args.module:
            cmec_unregister(args.module, config_file)
        else:
            print("Usage: python cmec-driver.py unregister <mod dir>")

    # List
    if args.command == "list":
        if args.all:
            cmec_list(True)
        elif not args.all:
            cmec_list(False)
        else:
            print("Usage: python cmec-driver.py list -all")

    # Execute
    if args.command == "run":
        config_dir = config_file.parents[0]
        if (args.obs and args.model and args.output and args.module):
            cmec_run(args.model, args.output, args.module, config_dir, args.obs)
        elif (args.model and args.output and args.module):
            cmec_run(args.model, args.output, args.module, config_dir)
        else:
            print(
                "Usage: python cmec-driver.py run "
                + "-obs <obs dir> <model dir> <out dir> <mod names>")
