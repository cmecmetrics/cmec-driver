"""
CMEC driver

Interface for running CMEC-compliant modules.

Examples:
    Add conda install information::

    $ python cmec_driver.py setup -conda_source <path_to_conda>
    $ python cmec_driver.py setup -conda_source ~/miniconda3/etc/profile.d/conda.sh

    Remove conda install information::

    $ python cmec_driver.py setup -remove_conda

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
import glob
import json
import string
import sys
import os

version = "20210610"
cmec_library_name = ".cmeclibrary"
cmec_toc_name = "contents.json"
cmec_settings_name = "settings.json"
cmec_settings_name_alt = "settings.jsonc"


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

def get_mdtf_env(pod_name, runtime_requirements):
    """Return mdtf environment.
    Some borrowing from MDTF environment manager script
    """
    mdtf_prefix = "_MDTF_"
    if pod_name in ["convective_transition_diag","ENSO_MSE"]:
        # This pod has unique env
        return mdtf_prefix + pod_name
    else:
        langs = [s.lower() for s in runtime_requirements]
        if ('r' in langs) or ('rscript' in langs):
            return mdtf_prefix + 'R_base'
        elif 'ncl' in langs:
            return mdtf_prefix + 'NCL_base'
        elif 'python2' in langs:
            raise CMECError("MDTF POD error: Python 2 not supported for new PODs.")
        elif 'python3' in langs:
            return mdtf_prefix + 'python3_base'
        else:
            raise CMECError("MDTF POD environment not found")

def mdtf_translate_var(varname, convention, mPath):
    fieldlist_path = Path(mPath).parents[1] / Path("data")
    fieldlist_file = "fieldlist_" + convention + ".jsonc"
    with open(fieldlist_path / Path("fieldlist_CMIP.jsonc"), "r") as fieldlist:
        flist_cmip = json.loads("\n".join(row for row in fieldlist if (not row.lstrip().startswith("//")) and (row.find(", //") < 0)))["variables"]

    try:
        with open(fieldlist_path / fieldlist_file, "r") as fieldlist:
            flist = json.loads("\n".join(row for row in fieldlist if not (row.lstrip().startswith("//")) and (row.find(", //") < 0)))["variables"]
    except FileNotFoundError:
        raise CMECError("Fieldlist for convention " + convention + " not found.")

    standard_name = flist_cmip[varname]["standard_name"]
    for model_var in flist:
        if flist[model_var]["standard_name"] == standard_name:
            return model_var

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

    def clear(self):
        self.path = ""
        self.map_module_path_list = {}
        self.jlib = {"modules": {}, "cmec-driver": {}, "version": version}

    def initialize_path(self):
        """Get the path for the .cmeclibrary file"""
        homedir = Path.home()

        if homedir.exists():
            self.path = homedir / cmec_library_name

    def read(self):
        """Load the contents of the CMEC library.

        Loads the .cmeclibrary file as a json and checks that the
        contents and formatting match CMEC standards.
        """
        # Clear the library
        self.clear()

        # Initialize path
        self.initialize_path()

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

    def write(self):
        self.initialize_path()

        with open(self.path, "w") as outfile:
            json.dump(self.jlib, outfile)

    def insert(self, module_name, filepath):
        """Add a module to the library.

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

    def remove(self, module_name):
        if module_name not in self.map_module_path_list:
            raise CMECError("Module " + module_name + " not found in library")

        if module_name not in self.jlib["modules"]:
            raise CMECError("Module appears in map but not in json representation")

        # Remove from map and json
        self.map_module_path_list.pop(module_name)
        self.jlib["modules"].pop(module_name)

    def size(self):
        """Get the number of modules in the library."""
        return len(self.map_module_path_list)

    def find(self, strModule):
        """Get the path to a specific module."""
        return self.map_module_path_list.get(strModule,"")

    def get_module_list(self):
        """Get a list of the modules in the library."""
        return [*self.map_module_path_list]

    def get_conda_root(self):
        """Return path to conda install."""
        return self.jlib.get("conda_root",None)

    def set_conda_root(self, conda_root):
        self.jlib["conda_root"] = conda_root

    def clear_conda_root(self):
        self.jlib.pop("conda_root", None)

    def get_env_root(self):
        return self.jlib.get("conda_env_root",None)

    def set_env_root(self, env_dir):
        self.jlib["conda_env_root"] = env_dir

    def clear_env_root(self):
        self.jlib.pop("conda_env_root")

    def is_pod(self, strModule):
        """Return true if module is part of MDTF diagnostics package."""
        filepath = Path(self.find(strModule)).resolve()
        if filepath is not False:
            if "diagnostics" in filepath.parents[0].name:
                if "MDTF-diagnostics" in filepath.parents[1].name:
                    return True
        return False

class CMECModuleSettings():
    """Interface with module settings file."""
    def __init__(self):
        self.path = ""
        self.jsettings = {}

    def exists_in_module_path(self, filepath):
        """Check if a settings file exists for a module.

        Returns settings path if settings.json found in path, otherwise False.

        Args:
            filepath (str or Path): path for the module directory
        """
        if not isinstance(filepath, Path):
            filepath = Path(filepath)

        path_settings = filepath / cmec_settings_name
        if not path_settings.exists():
            # try alternate jsonc name
            path_settings = filepath / cmec_settings_name_alt
            if not path_settings.exists():
                # no settings
                path_settings = False

        return path_settings

    def clear(self):
        self.path = ""
        self.jsettings = {}

    def read_from_file(self, path_settings):
        """Read the CMEC module contents file.

        Loads the contents file as a json and checks that the contents
        match CMEC standards.
        """
        self.clear()

        if not isinstance(path_settings, Path):
            path_settings = Path(path_settings)

        self.path = path_settings

        with open(self.path, "r") as cmec_json:
            # Settings could be a JSONC
            self.jsettings = json.loads(
                "\n".join(row for row in cmec_json if not row.lstrip().startswith("//")))

        if "settings" not in self.jsettings:
            raise CMECError(
                "Malformed CMEC settings file "
                + str(path_settings) + ": missing key 'settings'")

        if "driver" not in self.jsettings["settings"]:
            raise CMECError(
                "Malformed CMEC settings file "
                + str(path_settings) + ": missing key 'settings': 'driver'd")

        for key in ["name","long_name"]:
            if key not in self.jsettings["settings"]:
                # Replace missing names with driver script name
                self.jsettings["settings"][key] = Path(self.jsettings["settings"]["driver"]).stem

    def create_config(self, module_name=''):
        """Adds module specific user settings to cmec config json."""
        config_name = self.get_name()
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
        config_file = CMECConfig()
        try:
            config_file.read()
        except CMECError:
            rewrite = user_prompt("Overwrite cmec.json?")
            if not rewrite:
                print("*** Skip writing default parameters. Warning: This may affect module performance. ***")
                return
        config_file.update(module_settings)
        config_file.write()

    def remove_config(self, module_name=''):
        config_name = self.get_name()
        if module_name != '':
            config_name = module_name + '/' + config_name
        config_file = CMECConfig()
        try:
            config_file.read()
        except CMECError:
            print("Skipping cmec.json clean up")
            return
        config_file.remove(config_name)
        config_file.write()

    def get_name(self):
        """Returns the module name."""
        if "name" in self.jsettings["settings"]:
            name=self.jsettings["settings"]["name"]
        else:
            name=self.jsettings["settings"]["long_name"]
        return name

    def get_long_name(self):
        """Returns module long name."""
        return self.jsettings["settings"]["long_name"]

    def get_driver_script(self):
        """Returns driver file name."""
        return self.jsettings["settings"]["driver"]

    def get_setting(self,key):
        """Returns setting from settings dict."""
        if key in self.jsettings:
            return self.jsettings[key]
        return {}


class CMECModuleTOC():
    """Interface with module contents file."""
    def __init__(self):
        self.path = ""
        self.map_configs = {}
        self.jcmec = {}
        self.jcontents = {}

    def exists_in_module_path(self, path_module):
        """Check if contents file exists for module.

        Returns True if contents.json found in module directory.
        Otherwise, returns False.

        Args:
            path_module (str or Path): path to module directory
        """
        if not isinstance(path_module, Path):
            path_module = Path(path_module)

        path_settings = path_module / cmec_toc_name

        return path_settings.exists()

    def clear(self):
        self.path = ""
        self.map_configs = {}
        self.jcmec = {}
        self.jcontents = {}

    def read_from_module_path(self, path_module):
        """Read the CMEC module contents file.

        Loads the contents.json for the specified module and
        checks that the json matches the CMEC standards.

        Args:
            path_module (str or Path): path to the module directory
        """
        # Clear and get path
        self.clear()

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
                cmec_settings.read_from_file(path_settings)
                self.map_configs[cmec_settings.get_name()] = path_settings

            else:
                print(
                    "Malformed CMEC Library file: an entry of the"
                    + "'contents' array is not of type string")

    def insert(self, config_name, filepath):
        """Add a configuration.

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

        # insert module
        self.map_configs[config_name] = filepath

        self.jcmec["contents"][config_name] = str(filepath)

    def create_config(self, path_module):
        """Create module settings json for each configuration."""
        for item in self.jcontents:
            if isinstance(item, str):
                cmec_settings = CMECModuleSettings()
                path_settings = path_module / item
                cmec_settings.read_from_file(path_settings)
                cmec_settings.create_config(self.get_name())

    def remove_config(self, path_module):
        for item in self.jcontents:
            if isinstance(item, str):
                cmec_settings = CMECModuleSettings()
                path_settings = path_module/item
                cmec_settings.read_from_file(path_settings)
                cmec_settings.remove_config(self.get_name())

    def get_name(self):
        """Return the name of the module."""
        return self.jcmec["module"]["name"]

    def get_long_name(self):
        """Return the long name of the module."""
        return self.jcmec["module"]["long_name"]

    def size(self):
        """Return the number of configs."""
        return len(self.map_configs)

    def config_list(self):
        """Return the list of configs."""
        return [*self.map_configs]

    def find(self, setting):
        """Return the setting file path."""
        if setting in self.map_configs:
            return self.map_configs[setting]
        return False


class CMECConfig():
    """Access CMEC config file cmec.json"""
    def __init__(self):
        self.path = Path(__file__).absolute().parents[0] / Path("config/cmec.json")
        if not self.path.exists():
            with open(self.path,"w") as cfile:
                json.dump({}, cfile, indent=4)

    def read(self):
        try:
            with open(self.path, "r") as cfile:
                all_settings = json.load(cfile)
        except json.decoder.JSONDecodeError:
            raise CMECError("Could not load config/cmec.json. File might not be valid JSON")

        # enforce dictionary if config is empty
        if isinstance(all_settings, dict):
            self.settings = all_settings
        else:
            self.settings = {}

    def get_module_settings(self, str_module):
        return self.settings.get(str_module,None)

    def update(self,module_dict):
        """Add key/value object to config json."""
        self.settings.update(module_dict)

    def remove(self,str_module):
        """Remove entry for str_module from config.json."""
        self.settings.pop(str_module, None)

    def write(self):
        with open(self.path, "w") as cfile:
            json.dump(self.settings, cfile, indent=4)


def cmec_setup(conda_source=None,env_dir=None,remove_conda=False):
    """Set up conda environment.
    Args:
        **kwargs:
            conda_source (str): path to conda installation directory
            remove_conda (bool): to clear conda_source from library
    """
    print("Reading CMEC library")
    lib = CMECLibrary()
    lib.read()

    if conda_source is not None:
        print("Validating conda install location")
        if not Path(conda_source).exists():
            raise CMECError("Conda install location does not exist")
        print("Setting conda root")
        lib.set_conda_root(conda_source)
    if env_dir is not None:
        print("Validating environment directory")
        if not Path(env_dir).exists():
            raise CMECError("Environment directory does not exist")
        print("Setting environment root")
        lib.set_env_root(env_dir)
    if remove_conda:
        print("Clearing conda settings")
        lib.clear_conda_root()
        lib.clear_env_root()

    print("Writing CMEC library")
    lib.write()

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
    tmp_settings_name = cmec_settings.exists_in_module_path(module_dir)
    if tmp_settings_name:
        print("Validating " + cmec_settings_name)
        cmec_settings.read_from_file(tmp_settings_name)
        str_name = cmec_settings.get_name()
        print("Writing default settings to " + str(config_file.relative_to(Path.cwd())))
        cmec_settings.create_config()

    # or check if module contains a contents file
    elif cmec_toc.exists_in_module_path(module_dir):
        print("Validating " + cmec_toc_name)
        cmec_toc.read_from_module_path(module_dir)
        print("Writing default settings to " + str(config_file.relative_to(Path.cwd())))
        cmec_toc.create_config(module_dir)

        str_name = cmec_toc.get_name()
        str_long_name = cmec_toc.get_long_name()

        print("Module " + str_name + " " + str_long_name)
        print("Contains " + str(cmec_toc.size()) + " configurations")
        print("------------------------------------------------------------")
        for item in cmec_toc.config_list():
            print(str_name + "/" + item)
        print("------------------------------------------------------------")

    else:
        raise CMECError(
            "Module path must contain "
            + cmec_toc_name + " or " + cmec_settings_name)

    # Add to CMEC library
    print("Reading CMEC library")
    lib = CMECLibrary()
    lib.read()

    print("Adding new module to library")
    lib.insert(str_name, module_dir)

    print("Writing CMEC library")
    lib.write()


def cmec_unregister(module_name, config_file):
    """Remove a module from the cmec library.

    Args:
        module_name (str): name of module to remove
    """
    print("Reading the CMEC library")
    lib = CMECLibrary()
    lib.read()

    print("Removing configuration")
    module_dir = lib.find(module_name)
    cmec_settings = CMECModuleSettings()
    cmec_toc = CMECModuleTOC()
    tmp_settings_name = cmec_settings.exists_in_module_path(module_dir)
    if tmp_settings_name:
        cmec_settings.read_from_file(tmp_settings_name)
        cmec_settings.remove_config()
    elif cmec_toc.exists_in_module_path(module_dir):
        cmec_toc.read_from_module_path(module_dir)
        cmec_toc.remove_config(module_dir)

    print("Removing module")
    lib.remove(module_name)

    print("Writing CMEC library")
    lib.write()

def cmec_list(listAll):
    """List modules in cmec library.

    Args:
        listAll (bool): if True, list configurations
    """
    print("Reading CMEC library")
    lib = CMECLibrary()
    lib.read()

    # Check for size zero library
    if lib.size() == 0:
        raise CMECError("CMEC library contains no modules")

    cmec_toc = CMECModuleTOC()

    # List modules
    print("CMEC library contains " + str(lib.size()) + " modules")
    print("------------------------------------------------------------")
    for module in lib.get_module_list():
        module_dir = lib.find(module)
        if cmec_toc.exists_in_module_path(module_dir):
            cmec_toc.read_from_module_path(module_dir)
            print(
                " " + module + " [" + str(cmec_toc.size())
                + " configurations]" )

            if listAll:
                for config in cmec_toc.config_list():
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
    lib.read()

    # Build dirver script list
    print("Identifying drivers")

    module_path_list = []
    driver_script_list = []
    working_dir_list = []
    pod_varlist = {}
    pod_frequency = {}
    pod_runtime = {}
    mdtf_path = {}

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

        # Check if module is pod
        mod_is_pod = lib.is_pod(module)

        # Check if module contains a settings file
        cmec_settings = CMECModuleSettings()
        cmec_toc = CMECModuleTOC()

        tmp_settings_name = cmec_settings.exists_in_module_path(module_path)
        if tmp_settings_name:
            if str_configuration != "":
                raise CMECError(
                    "Module " + str_parent_module
                    + " only contains a single configration")

            cmec_settings.read_from_file(tmp_settings_name)
            module_path_list.append(module_path)
            driver_script_list.append(module_path / cmec_settings.get_driver_script())
            working_dir_list.append(Path(cmec_settings.get_name()))

        # Check if module contains a contents file
        elif cmec_toc.exists_in_module_path(module_path):
            cmec_toc.read_from_module_path(module_path)
            settings = cmec_toc.config_list()
            config_found = False

            for setting in settings:
                if str_configuration in ("", setting):
                    setting_path = cmec_toc.find(setting)
                    cmec_settings.read_from_file(setting_path)
                    module_path_list.append(setting_path.parents[0])
                    driver_script_list.append(module_path / cmec_settings.get_driver_script())
                    working_dir_list.append(Path(cmec_toc.get_name()) / Path(cmec_settings.get_name()))
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

        if mod_is_pod:
            pod_varlist[module] = cmec_settings.get_setting("varlist")
            pod_frequency[module] = cmec_settings.get_setting("data")["frequency"]
            pod_runtime[module] = cmec_settings.get_setting("settings")["runtime_requirements"]
            mdtf_path[module] = Path(module_path).resolve().parents[1]

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
    # If MDTF POD, read env variables from a few different files.
    print("The following environment variables will be set:")
    print("------------------------------------------------------------")
    print("CMEC_OBS_DATA=" + str(obspath))
    print("CMEC_MODEL_DATA=" + str(modpath))
    print("CMEC_WK_DIR=" + str(workpath) + "/$MODULE_NAME")
    print("CMEC_CODE_DIR=$MODULE_PATH")
    print("CMEC_CONFIG_DIR=" + str(config_dir))
    if mod_is_pod:
        print("along with additional MDTF POD environment variables")
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
        path_out_model = path_out / "model" / "netcdf"
        path_out_model.mkdir(parents=True)
        path_out_model = path_out / "model" / "PS"
        path_out_model.mkdir(parents=True)

    # Create command scripts
    env_scripts = []
    for driver, workingDir, mPath, module in zip(driver_script_list, working_dir_list, module_path_list, module_list):
        path_working_dir = workpath / workingDir
        path_script = path_working_dir / "cmec_run.bash"
        env_scripts.append(path_script)
        print(str(path_script))
        # resolve paths for writing if they exist:
        module_path_full = mPath.resolve()
        modpath_full = modpath.resolve()
        working_full = path_working_dir.resolve()
        config_full = config_dir.resolve()
        obspath_full = None
        if obspath is not None:
            obspath_full = obspath.resolve()
        else:
            obspath_full = "None"
        script_lines = []
        with open(path_script, "w") as script:
            script_lines.append("#!/bin/bash\n")
            script_lines.append("export CMEC_CODE_DIR=%s\n" % module_path_full)
            script_lines.append("export CMEC_OBS_DATA=%s\n" % obspath_full)
            script_lines.append("export CMEC_MODEL_DATA=%s\n" % modpath_full)
            script_lines.append("export DATADIR=%s\n" % modpath_full)
            script_lines.append("export CMEC_WK_DIR=%s\n" % working_full)
            script_lines.append("export CMEC_CONFIG_DIR=%s\n" % config_full)
            script_lines.append("export CONDA_SOURCE=%s\n" % lib.get_conda_root())
            script_lines.append("export CONDA_ENV_ROOT=%s\n" % lib.get_env_root())
            if mod_is_pod:
                print(module)
                # write pod env
                cmec_config = CMECConfig()
                cmec_config.read()
                pod_settings = cmec_config.get_module_settings(module)
                script_lines.append("export OBS_DATA=%s\n" % obspath_full)
                script_lines.append("export DATADIR=%s\n" % modpath_full)
                script_lines.append("export POD_HOME=%s\n" % module_path_full)
                script_lines.append("export WK_DIR=%s\n" % working_full)
                script_lines.append("export RGB=%s\n" % str(Path(mdtf_path[module])  / Path("shared") / Path("rgb")))
                for item in pod_settings:
                    script_lines.append("export %s=%s\n" % (item, pod_settings[item]))
                for varname in pod_varlist[module]:
                    env_var = varname.upper()+"_FILE"
                    env_basename = Path("%s.%s.%s.nc" % (pod_settings["CASENAME"], varname, pod_frequency[module]))
                    env_path = modpath_full / Path(pod_settings["CASENAME"]) / Path(pod_frequency[module]) / env_basename
                    script_lines.append("export %s=%s\n" % (env_var,env_path))
                    script_lines.append("export %s=%s\n" % (varname+"_var",varname))
                env_name = get_mdtf_env(module, pod_runtime[module])
                script_lines.append("source $CONDA_SOURCE\nconda activate $CONDA_ENV_ROOT/%s\n" % env_name)
            if driver.suffix == ".py":
                script_lines.append("python %s\n" % driver)
            else:
                script_lines.append("%s\n" % driver)
            script.writelines(script_lines)
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
        help="commands are 'install', 'register', 'unregister', 'run', 'list'",
        dest="command")
    parser_inst = subparsers.add_parser(
        "setup", help="register conda installation directory")
    parser_reg = subparsers.add_parser(
        "register", help="add module to cmec library")
    parser_unreg = subparsers.add_parser(
        "unregister", help="remove module from cmec library")
    parser_list = subparsers.add_parser(
        "list", help="list modules in cmec library")
    parser_run = subparsers.add_parser(
        "run", help="run chosen modules")

    parser_inst.add_argument("-conda_source", default=None, type=str)
    parser_inst.add_argument("-env_root", default=None, type=str)
    parser_inst.add_argument("-remove_conda", action="store_true", default=False)
    parser_reg.add_argument("modpath", type=str)
    parser_unreg.add_argument("module")
    parser_list.add_argument("-all", action="store_true", default=False,
        help="list modules and configurations")
    parser_run.add_argument("-obs", default="", help="observations directory")
    parser_run.add_argument("model", help="model directory")
    parser_run.add_argument("output", help="output directory")
    parser_run.add_argument("module", nargs="+", help="module names")

    # get the rest of the arguments
    args = parser.parse_args()

    # cmec config goes in cmec-driver/config folder
    config_file = Path(__file__).absolute().parents[0] / Path("config/cmec.json")

    # Install
    if args.command == "setup":
        cmec_setup(
            conda_source=args.conda_source,
            env_dir=args.env_root,
            remove_conda=args.remove_conda)

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
