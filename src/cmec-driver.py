"""
CMEC driver

Interface for running CMEC-compliant modules.

Examples:
    Registering a module::

    $ python cmec_driver.py register -modulePath <module_directory_path>
    $ python cmec_driver.py register -modulePath ~/modules/ILAMB

    Unregistering a module::

    $ python cmec_driver.py unregister -module <module_name>
    $ python cmec_driver.py unregister ILAMB

    List modules::

    $ python cmec_driver.py list -all

    Run a module::

    $ python cmec_driver.py run -obs <observations_folder> -model <model_folder> -output <output_folder> -module <module_name>
    $ python cmec_driver.py run -obs ./obs -model ./model -output ./output -module PMP/meanclimate

Attributes:
    version (str): CMEC driver version
    cmecLibraryName (str): standard file name for cmec library
    cmecTOCName (str): standard file name for module contents
    cmecSettingsName (str): standard file name for module settings

Todo:
Improve flag usage
Add tests
Clean up style
Unregister muliple modules at once?
"""
from pathlib import Path
import json
import sys
import os
import string

version = "20201114"
cmecLibraryName = ".cmeclibrary"
cmecTOCName = "contents.json"
cmecSettingsName = "settings.json"


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
        elif choice in valid:
            return valid[choice]
        else:
            sys.stdout.write("Please respond 'y' or 'n' ")


class CMECError(Exception):
    """Errors related to CMEC standards.

    Args:
        message (str): Explanation of the error
    """
    def __init__(self, message):
        self.message = message


class CMECLibrary():
    """Interact with the CMEC library.

    The CMEC library file (~/.cmeclibrary) is, most simply, a json
    containing the keys "modules", "cmec-driver", and "version". This
    class can initialize a new library, read from the library, and edit
    the library.
    """
    def __init__(self):
        self.mapModulePaths = {}
        self.jlib = {"modules": {}, "cmec-driver": {}, "version": version}

    def Clear(self):
        self.path = ""
        self.mapModulePaths = {}
        self.jlib = {"modules": {}, "cmec-driver": {}, "version": version}

    def InitializePath(self):
        """Get the path for the .cmeclibrary file"""
        homedir = Path.home()

        if homedir.exists():
            self.path = homedir / cmecLibraryName

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
                raise CMECError("Malformed CMEC library file missing key " + key)

            if not isinstance(key, str):
                raise CMECError("Malformed CMEC library file: " + key + " is not of type string")

        for key in self.jlib["modules"]:
            if not isinstance(self.jlib["modules"][key], str):
                raise CMECError("Malformed CMEC library file: an entry of the 'modules' array is not of type string")

            if key in self.mapModulePaths:
                raise CMECError("Malformed CMEC library file: Repeated module name " + key)

            self.mapModulePaths[key] = Path(self.jlib["modules"][key])

    def Write(self):
        self.InitializePath()

        with open(self.path, "w") as outfile:
            json.dump(self.jlib, outfile)

    def Insert(self,strModuleName, filepath):
        """Add a module to the library

        Args:
            strModuleName (str): name of module
            filepath (str or Path): path to the module directory
        """
        # Check if module already exists:
        if strModuleName in self.mapModulePaths:
            print("Module already exists in library; if path has changed first run 'unregister'")
            return

        if not isinstance(filepath, Path):
            if not isinstance(filepath, str):
                raise CMECError("Malformed path is not of type string or pathlib.Path")
            else:
                filepath = Path(filepath)

        # Insert module
        self.mapModulePaths[strModuleName] = filepath
        self.jlib["modules"][strModuleName] = str(filepath)


    def Remove(self,strModuleName):
        if strModuleName in self.mapModulePaths:
            filepath = self.mapModulePaths[strModuleName]
        else:
            raise CMECError("Module " + strModuleName + " not found in library")

        if strModuleName not in self.jlib["modules"]:
            raise CMECError("Module appears in map but not in json representation")

        # Remove from map and json
        self.mapModulePaths.pop(strModuleName)
        self.jlib["modules"].pop(strModuleName)

    def size(self):
        """Get the number of modules in the library"""
        return len(self.mapModulePaths)

    def find(self, strModule):
        """Get the path to a specific module"""
        if strModule in self.mapModulePaths:
            return self.mapModulePaths[strModule]
        else:
            return False

    def getModuleList(self):
        """Get a list of the modules in the library"""
        return [key for key in self.mapModulePaths]


class CMECModuleSettings():
    """Interface with module settings file"""
    def __init__(self):
        self.jsettings = {}

    def ExistsInModulePath(self, filepath):
        """Check if a settings file exists for a module.

        Returns True if settings.json found in path, otherwise False.

        Args: 
            filepath (str or Path): path for the module directory
        """
        if not isinstance(filepath, Path):
            filepath = Path(filepath)

        pathSettings = filepath / cmecSettingsName

        return pathSettings.exists()

    def Clear(self):
        self.path = ""
        self.jsettings = {}

    def ReadFromFile(self, pathSettings):
        """Read the CMEC module contents file.

        Loads the contents file as a json and checks that the contents
        match CMEC standards.
        """
        self.Clear()

        if not isinstance(pathSettings, Path):
            pathSettings = Path(pathSettings)

        self.path = pathSettings

        with open(self.path, "r") as cmecjson:
            self.jsettings = json.load(cmecjson)

        for key in ["settings", "obslist"]:
            if key not in self.jsettings:
                raise CMECError("Malformed CMEC settings file " + str(pathSettings) + ": missing key " + key)

        for key in ["name", "long_name", "driver"]:
            if key not in self.jsettings["settings"]:
                raise CMECError("Malformed CMEC settings file " + str(pathSettings) + ": missing key settings:" + key)
                # also check type

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
        self.mapConfigs = {}
        self.jcmec = {}
        self.jcontents = {}

    def ExistsInModulePath(self, pathModule):
        """Check if contents file exists for module

        Returns True if contents.json found in module directory. 
        Otherwise, returns False.

        Args:
            pathModule (str or Path): path to module directory
        """
        if not isinstance(pathModule, Path):
            pathModule = Path(pathModule)

        pathSettings = pathModule / cmecTOCName

        return pathSettings.exists()

    def Clear(self):
        self.path = ""
        self.mapConfigs = {}
        self.jcmec = {}
        self.jcontents = {}

    def ReadFromModulePath(self, pathModule):
        """Read the CMEC module contents file
        
        Loads the contents.json for the specified module and
        checks that the json matches the CMEC standards.

        Args:
            pathModule (str or Path): path to the module directory
        """
        # Clear and get path
        self.Clear()

        if not isinstance(pathModule, Path):
            pathModule = Path(pathModule)

        self.path = pathModule / cmecTOCName

        # Parse and validate CMEC json
        with open(self.path, "r") as cmectoc:
            self.jcmec = json.load(cmectoc)

        for key in ["module", "contents"]:
            if key not in self.jcmec:
                raise CMECError("Malformed CMEC library file " + self.path + ": missing key " + key)

        for key in ["name", "long_name"]:
            if key not in self.jcmec["module"]:
                raise CMECError("Malformed CMEC library file " + self.path + ": missing key module:" + key)

        if isinstance(self.jcmec["contents"], list):
            self.jcontents = self.jcmec["contents"]
        else:
            print("Malformed CMEC library file:'contents' is not of type list")

        for item in self.jcontents:
            if isinstance(item, str):
                cmecsettings = CMECModuleSettings()
                pathSettings = pathModule / item
                cmecsettings.ReadFromFile(pathSettings)
                self.mapConfigs[cmecsettings.GetName()] = pathSettings

            else:
                print("Malformed CMEC Library file: an entry of the 'contents' array is not of type string")

    def Insert(self, strConfigName, filepath):
        """Add a configuration

        Args:
            strConfigName (str): name of configuration
            filepath (str or Path): path to the configuration file
        """
        # Check if config already exists
        if self.mapConfigs(strConfigName):
            print("Repeated configuration name " + strConfigName)
            return

        if not isinstance(filepath, Path):
            filepath = Path(filepath)

        # Insert module
        self.mapConfigs[strConfigName] = filepath

        self.jcmec["contents"][strConfigName] = str(filepath)

    def getName(self):
        """Return the name of the module"""
        return self.jcmec["module"]["name"]

    def getLongName(self):
        """Return the long name of the module"""
        return self.jcmec["module"]["long_name"]

    def size(self):
        """Return the number of configs"""
        return len(self.mapConfigs)

    def configList(self):
        """Return the list of configs"""
        return [key for key in self.mapConfigs]

    def find(self, setting):
        """Return the setting file path"""
        if setting in self.mapConfigs:
            return self.mapConfigs[setting]
        else:
            return False


def cmec_register(strDirectory):
    """Add a module to the cmec library.

    Args:
        strDirectory (str or Path): path to the module directory
    """
    if not isinstance(strDirectory, Path):
        strDirectory = Path(strDirectory)
    
    print("Registering " + str(strDirectory))

    cmecsettings = CMECModuleSettings()
    cmectoc = CMECModuleTOC()

    # check if module contains a settings file
    if cmecsettings.ExistsInModulePath(strDirectory):
        print("Validating " + cmecSettingsName)

        cmecsettings.ReadFromFile(strDirectory / cmecSettingsName)

        strName = cmecsettings.GetName()

    # or check if module contains a contents file
    elif cmectoc.ExistsInModulePath(strDirectory):
        print("Validating " + cmecTOCName)

        cmectoc.ReadFromModulePath(strDirectory)

        strName = cmectoc.getName()
        strLongName = cmectoc.getLongName()

        print("Module " + strName + strLongName)
        print("Contains " + str(cmectoc.size()) + " configurations")
        print("------------------------------------------------------------")
        for item in cmectoc.configList():
            print(strName + "/" + item)
        print("------------------------------------------------------------")

    else:
        raise CMECError("Module path must contain " + cmecTOCName + " or " + cmecSettingsName)

    # Add to CMEC library
    print("Reading CMEC library")
    lib = CMECLibrary()
    lib.Read()

    print("Adding new module to library")
    lib.Insert(strName, strDirectory)

    print("Writing CMEC library")
    lib.Write()


def cmec_unregister(strModuleName):
    """Remove a module from the cmec library.

    Args: 
        strModuleName (str): name of module to remove
    """
    print("Reading the CMEC library")
    lib = CMECLibrary()
    lib.Read()

    print("Removing module")
    lib.Remove(strModuleName)

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
    if (lib.size() == 0):
        raise CMECError("CMEC library contains no modules")

    cmectoc = CMECModuleTOC()

    # List modules
    print("CMEC library contains " + str(lib.size()) + " modules")
    print("------------------------------------------------------------")
    for module in lib.getModuleList():
            modPath = lib.find(module)
            if cmectoc.ExistsInModulePath(modPath):
                cmectoc.ReadFromModulePath(modPath)
                print(" " + module + " [" + str(cmectoc.size()) + " configurations]" )

                if listAll:
                    for config in cmectoc.configList():
                        print("    " + module + "/" + config)
    print("------------------------------------------------------------")


def cmec_run(strObsDir, strModelDir, strWorkingDir, vecModules):
    """Run a module from the cmec library.

    Args:
        strObsDir (str or Path): path to observation directory
        strModelDir (str or Path): path to model directory
        strWorkingDir (str or Path): path to output directory
        vecModules (list of strings): List of the module names to run

    Todo:
    Handle case with no observations
    Wrap text printed to cmec_run.bash
    """

    # Verify existence of each directory
    dirList = {"Observation": strObsDir, "Model": strModelDir, "Working": strWorkingDir}

    for key in dirList: 
        if isinstance(dirList[key],str) and len(dirList[key]) == 0:
            raise CMECError(key + " data path not specified")
        else:
            tmpdir = dirList[key]
            if isinstance(tmpdir, str):
                tmpdir = Path(tmpdir)
            if tmpdir.absolute().is_dir():
                dirList[key] = tmpdir.absolute()
            else:
                raise CMECError(str(tmpdir.absolute()) + " does not exist or is not a directory")

    obsPath = dirList["Observation"]
    modPath = dirList["Model"]
    workPath = dirList["Working"]

    # Load the CMEC library
    print("Reading CMEC library")
    lib = CMECLibrary()
    lib.Read()

    # Build dirver script list
    print("Identifying drivers")

    vecModulePaths = []
    vecDriverScripts = []
    vecWorkingDirs = []

    for module in vecModules:
        # Get name of base module
        for char in module.lower():
            if char not in string.ascii_lowercase + string.digits + "_" + "/":
                raise CMECError("Non-alphanumeric characters found in module name " + module)

        strParentModule = module
        strConfiguration = ""
        if "/" in module:
            strParentModule, strConfiguration = module.split("/")

        # Check for base module in library
        modulePath = lib.find(strParentModule)
        if not modulePath:
            raise CMECError("Module " + strParentModule + " not found in CMEC library")

        # Check if module contains a settings file
        cmecsettings = CMECModuleSettings()
        cmectoc = CMECModuleTOC()

        if cmecsettings.ExistsInModulePath(modulePath):
            #if strConfiguration != "":
            #   return print("ERROR: Module " + strParentModule + " only contains a single configuration")
            cmecsettings.ReadFromFile(modulePath / cmecSettingsName)

            vecModulePaths.append(modulePath)
            vecDriverScripts.append(modulePath / cmecsettings.GetDriverScript())
            vecWorkingDirs.append(Path(cmecsettings.GetName()))

        # Check if module contains a contents file
        elif cmectoc.ExistsInModulePath(modulePath):
            cmectoc.ReadFromModulePath(modulePath)
            settings = cmectoc.configList()
            configFound = False

            for setting in settings:
                if strConfiguration == setting:
                    settingPath = cmectoc.find(setting)
                    cmecsettings.ReadFromFile(settingPath)

                    vecModulePaths.append(settingPath)
                    vecDriverScripts.append(modulePath / cmecsettings.GetDriverScript())
                    vecWorkingDirs.append(Path(cmectoc.getName()) / Path(cmecsettings.GetName()))   
                    configFound = True

            if ((strConfiguration != "") and not configFound):
                raise CMECError("Module " + strParentModule + " does not contain configuration " + strConfiguration)    
        else:
            raise CMECError("Module " + strParentModule + " with path " + modulePath + " does not contain " + cmecSettingsName + " or " + cmecTOCName)  

    assert len(vecModulePaths) == len(vecDriverScripts)
    assert len(vecModulePaths) == len(vecWorkingDirs)

    # Check for zero drivers
    if not vecDriverScripts:
        raise CMECError("No driver files found")

    # Output driver file list
    print("The following " + str(len(vecDriverScripts)) + " modules will be executed:")
    print("------------------------------------------------------------")
    for workingDir, path, driver in zip(vecWorkingDirs, vecModules, vecDriverScripts):
        print("MODULE_NAME: " + str(workingDir))
        print("MODULE_PATH: " + str(path))
        print("  " + str(driver))
    print("------------------------------------------------------------")

    # Environment variables
    print("The following environment variables will be set:")
    print("------------------------------------------------------------")
    print("CMEC_OBS_DATA=" + str(obsPath))
    print("CMEC_MODEL_DATA=" + str(modPath))
    print("CMEC_WK_DIR=" + str(workPath) + "/$MODULE_NAME")
    print("CMEC_CODE_DIR=$MODULE_PATH")
    print("------------------------------------------------------------")

    # Create output directories
    print("Creating output directories")

    for driver, workingDir in zip(vecDriverScripts, vecWorkingDirs):
        pathOut = workPath / workingDir

        # Check for existence of output directories
        if pathOut.exists():
            question = "Path " + str(pathOut) + " already exists. Overwrite?"
            overwrite = user_prompt(question, default="yes")
            if overwrite:
                os_command = "rm -rf " + str(pathOut)
                os.system(os_command)
                # Check exit code?
            else:
                raise CMECError("Unable to clear output directory")

        # Create directories
        pathOut.mkdir(parents=True)

    # Create command scripts
    vecEnvScripts = []
    for driver, workingDir, mPath in zip(vecDriverScripts, vecWorkingDirs, vecModulePaths):
        pathMyWorkingDir = workPath / workingDir
        pathScript = pathMyWorkingDir / "cmec_run.bash"
        vecEnvScripts.append(pathScript)
        print(str(pathScript))
        with open(pathScript, "w") as script:
            script.write("""#!/bin/bash\nexport CMEC_CODE_DIR=%s\nexport CMEC_OBS_DATA=%s\nexport CMEC_MODEL_DATA=%s\nexport CMEC_WK_DIR=%s\n%s""" % (modulePath, obsPath, modPath, workPath, driver))
        os.system("chmod u+x " + str(pathScript))

    # Execute command scripts
    print("Executing driver scripts")
    for envScript, workDir in zip(vecEnvScripts, vecWorkingDirs):
        print("------------------------------------------------------------")
        print(str(workDir))
        os.system(str(envScript))
    print("------------------------------------------------------------")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description = "Process command line cmec-driver input")
    parser.add_argument("command")
    parser.add_argument("-obs")
    parser.add_argument("-model")
    parser.add_argument("-output")
    parser.add_argument("-modulePath")
    parser.add_argument("-module", nargs="+")
    parser.add_argument("-all", action='store_true')

    # get the rest of the arguments
    args = parser.parse_args()

    # Register
    if args.command == "register":
        if args.modulePath:
            cmec_register(args.modulePath)
        else:
            print("Usage: python cmec-driver.py register -module <mod dir>")

    # Unregister
    if args.command == "unregister":
        if args.module:
            cmec_unregister(args.module[0])
        else:
            print("Usage: python cmec-driver.py unregister -module <mod dir>")

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
        if (args.obs and args.model and args.output and args.module):
            cmec_run(args.obs, args.model, args.output, args.module)
        else:
            print("Usage: python cmec-driver.py run -obs <obs dir> -model <model dir> -output <out dir> -module <mod name>")
