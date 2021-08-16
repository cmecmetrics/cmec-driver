"""
"""
from pathlib import Path
import glob
import json
import string
import subprocess
import sys
import os

from cmec_global_vars import *

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
        """Return path to conda install"""
        return self.jlib.get("conda_source",None)

    def set_conda_root(self, conda_source):
        self.jlib["conda_source"] = conda_source

    def clear_conda_root(self):
        self.jlib.pop("conda_source", None)

    def get_env_root(self):
        return self.jlib.get("conda_env_root",None)

    def set_env_root(self, env_dir):
        self.jlib["conda_env_root"] = env_dir

    def clear_env_root(self):
        self.jlib.pop("conda_env_root")

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
                + str(path_settings) + ": missing key 'settings': 'driver'.")

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

class CMECIndex():
    """Class that handles top-level index.html."""
    def __init__(self,wkdir):
        self.text = []
        self.wkdir = Path(wkdir)
        self.html_file = Path(wkdir) / "index.html"
        self.html_list = Path(wkdir) / ".html_pages"

    def read(self):
        if self.html_list.exists():
            with open(self.html_list,"r") as f:
                self.html_page_dict = json.load(f)
        else:
            self.html_page_dict = {}

    def link_results(self,configuration,index_page):
        self.html_page_dict[configuration] = index_page

    def write(self):
        self.text = ["<html>",
            "<head><title>CMEC Driver Results</title></head>",
            "<h1>CMEC Driver Results</h1>"
            ]
        for module_name in sorted(list(self.html_page_dict)):
            # Add links for each page to html text
            if (self.wkdir / self.html_page_dict[module_name]).exists():
                new_text = '<br><a href="{0}">{1}</a>'.format(self.html_page_dict[module_name],module_name)
                self.text.append(new_text)
            else:
                # Clean up pages that don't exist now
                self.html_page_dict.pop(module_name)
        self.text.append("</html>")
        with open(self.html_file,"w") as f:
            f.writelines(self.text)
        # Update database of html index pages
        with open(self.html_list,"w") as f:
            json.dump(self.html_page_dict, f, indent=2)


class CMECConfig():
    """Access CMEC config file cmec.json"""
    def __init__(self):
        self.path = Path(__file__).absolute().parents[1] / Path("config/cmec.json")
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
