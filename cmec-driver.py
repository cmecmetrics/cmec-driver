"""
CMEC driver

Interface for running CMEC-compliant modules.

Examples:

    Add conda source information::

    $ python cmec-driver.py setup -conda_source <path_to_conda>
    $ python cmec-driver.py setup -conda_source ~/miniconda3/etc/profile.d/conda.sh

    Add environment directory::

    $ python cmec-driver.py setup -env_root <path_to_environments>
    $ python cmec-driver.py setup -env_root ~/miniconda3/envs

    Remove conda install information::

    $ python cmec-driver.py setup -clear_conda

    Registering a module::

    $ python cmec-driver.py register <module_directory_path>
    $ python cmec-driver.py register ~/modules/ILAMB

    Unregistering a module::

    $ python cmec-driver.py unregister <module_name>
    $ python cmec-driver.py unregister ILAMB

    List modules::

    $ python cmec-driver.py list -all

    Run a module::

    $ python cmec-driver.py run -obs <observations_folder> <model_folder> <output_folder> <module_name>
    $ python cmec-driver.py run -obs ./obs ./model ./output PMP/meanclimate

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
import subprocess
import sys
import os

sys.path.insert(0,"./src")
from file_handling import *
from mdtf_support import *
from utils import *
from cmec_global_vars import *

def cmec_setup(conda_source=None,env_dir=None,clear_conda=False):
    """Set up conda environment.
    Args:
        **kwargs:
            conda_source (str): path to conda installation directory
            env_dir (str): path to conda environment folder
            clear_conda (bool): to clear conda_source from library
    """
    if (conda_source is not None) | (env_dir is not None) | clear_conda:
        print("Reading CMEC library")
        lib = CMECLibrary()
        lib.Read()

        if conda_source is not None:
            print("Validating conda install location")
            if not Path(conda_source).exists():
                raise CMECError("Conda install location does not exist")
            print("Setting conda root")
            lib.setCondaRoot(conda_source)
        if env_dir is not None:
            print("Validating environment directory")
            if not Path(env_dir).exists():
                raise CMECError("Environment directory does not exist")
            print("Setting environment root")
            lib.setEnvRoot(env_dir)
        if clear_conda:
            print("Clearing conda settings")
            lib.clearCondaRoot()
            lib.clearEnvRoot()

        print("Writing CMEC library")
        lib.Write()

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

    # or check if module contains a contents file
    elif cmec_toc.exists_in_module_path(module_dir):
        print("Validating " + cmec_toc_name)
        cmec_toc.read_from_module_path(module_dir)

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

    # Write default settings to config
    if cmec_settings:
        print("Writing default settings to " + str(config_file.relative_to(Path.cwd())))
        cmec_settings.create_config(mod_is_pod=lib.is_pod(str_name))
    elif cmec_toc:
        print("Writing default settings to " + str(config_file.relative_to(Path.cwd())))
        cmec_toc.create_config(module_dir,mod_is_pod=lib.is_pod(str_name))


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

    # Build driver script list
    print("Identifying drivers")

    module_dict = {}
    driver_found = False

    for module in module_list:
        module_dict.update({module: {}})

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
        module_dict[module].update({"module_path": module_path})
        if not module_path:
            raise CMECError(
                "Module " + str_parent_module
                + " not found in CMEC library")

        # Check if module is pod
        mod_is_pod = lib.is_pod(module)
        module_dict[module].update({"mod_is_pod": mod_is_pod})

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
            module_dict[module].update({"module_path": module_path})
            module_dict[module].update({"driver_script": module_path/cmec_settings.get_driver_script()})
            module_dict[module].update({"working_dir": Path(cmec_settings.get_name())})
            module_dict[module].update({"working_dir_full": workpath/Path(cmec_settings.get_name())})

        # Check if module contains a contents file
        elif cmec_toc.exists_in_module_path(module_path):
            cmec_toc.read_from_module_path(module_path)
            settings = cmec_toc.config_list()
            config_found = False

            for setting in settings:
                if str_configuration in ("", setting):
                    setting_path = cmec_toc.find(setting)
                    cmec_settings.read_from_file(setting_path)
                    config_found = True
                    module_dict[module].update({"module_path": setting_path.parents[0]})
                    module_dict[module].update({"driver_script": module_path/cmec_settings.get_driver_script()})
                    module_dict[module].update({"working_dir": Path(cmec_toc.get_name())/Path(cmec_settings.get_name())})
                    module_dict[module].update({"working_dir_full": workpath/Path(cmec_toc.get_name())/Path(cmec_settings.get_name())})

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

        if module_dict[module]["driver_script"]:
            driver_found = True

        if module_dict[module]["mod_is_pod"]:
            module_dict[module]["pod_varlist"] = cmec_settings.get_setting("varlist")
            module_dict[module]["runtime"] = cmec_settings.get_setting("settings")["runtime_requirements"]
            module_dict[module]["pod_env_vars"] = cmec_settings.get_setting("settings").get("pod_env_vars",{})
            module_dict[module]["mdtf_path"] = Path(module_path).resolve().parents[1]
            module_dict[module]["dimensions"] = cmec_settings.get_setting("dimensions")
            module_dict[module]["alt_name"] = module_path.name
            data = cmec_settings.get_setting("data")
            #print(module_dict)
            #print("data: ", data)
            if data:
                module_dict[module]["frequency"] = data["frequency"]
            else:
                var1 = next(iter(module_dict[module]["pod_varlist"]))
                module_dict[module]["frequency"] = module_dict[module]["pod_varlist"][var1]["frequency"]

    # Check for zero drivers
    if not driver_found:
        raise CMECError("No driver files found")

    # Output driver file list
    print(
        "The following " + str(len(module_dict.keys()))
        + " modules will be executed:")
    print("------------------------------------------------------------")
    for module in module_dict:
        print("MODULE_NAME: " + str(module_dict[module]["working_dir"]))
        print("MODULE_PATH: " + str(module_dict[module]["module_path"]))
        print(" " + str(module_dict[module]["driver_script"]))
    print("------------------------------------------------------------")

    # Environment variables
    print("The following environment variables will be set:")
    print("------------------------------------------------------------")
    print("CMEC_OBS_DATA=" + str(obspath))
    print("CMEC_MODEL_DATA=" + str(modpath))
    print("CMEC_WK_DIR=" + str(workpath) + "/$MODULE_NAME")
    print("CMEC_CODE_DIR=$MODULE_PATH")
    print("CMEC_CONFIG_DIR=" + str(config_dir))
    print("along with additional MDTF POD environment variables as needed")
    print("------------------------------------------------------------")

    # Create output directories
    print("Creating output directories")
    for module in module_dict:
        path_out = module_dict[module]["working_dir_full"]

        # Check for existence of output directories
        if path_out.exists():
            question = "Path " + str(path_out) + " already exists. Overwrite?"
            overwrite = user_prompt(question, default="yes")
            if overwrite:
                os_command = "rm -rf " + str(path_out)
                subprocess.call(["rm","-rf",str(path_out)], shell=False)
                # Check exit code?
            else:
                raise CMECError("Unable to clear output directory")
        
        # Create new output directories directories
        path_out.mkdir(parents=True)
        if module_dict[module]["mod_is_pod"]:
            for folder in [path_out/"model"/"netcdf", path_out/"model"/"PS", path_out/"obs"]:
                path_out_tmp = folder
                path_out_tmp.mkdir(parents=True)

    # Resolve file paths for cmec_run.bash
    modpath_full = modpath.resolve()
    config_full = config_dir.resolve()
    if obspath is not None:
        obspath_full = obspath.resolve()
    else:
        obspath_full = "None"

    # Create command scripts
    for module in module_dict:
        path_out = module_dict[module]["working_dir_full"]
        path_script = path_out/"cmec_run.bash"
        module_dict[module].update({"env_script": path_script})
        print(str(path_script))
        # Resolve paths for env variables if they exist:
        module_path_full = module_dict[module]["module_path"].resolve()
        working_full = path_out.resolve()

        # Generate cmec_run.bash
        script_lines = []
        script_lines.append("#!/bin/bash\n")
        script_lines.append("export CMEC_CODE_DIR=%s\n" % module_path_full)
        script_lines.append("export CMEC_OBS_DATA=%s\n" % obspath_full)
        script_lines.append("export CMEC_MODEL_DATA=%s\n" % modpath_full)
        script_lines.append("export CMEC_WK_DIR=%s\n" % working_full)
        script_lines.append("export CMEC_CONFIG_DIR=%s\n" % config_full)
        script_lines.append("export CONDA_SOURCE=%s\n" % lib.get_conda_root())
        script_lines.append("export CONDA_ENV_ROOT=%s\n" % lib.get_env_root())

        if module_dict[module]["mod_is_pod"]:
            # Write pod env
            cmec_config = CMECConfig()
            cmec_config.read()
            pod_settings = cmec_config.get_module_settings(module)
            if "CASENAME" not in pod_settings:
                raise CMECError("'CASENAME' not found in module settings")
            script_lines.append("\n# MDTF POD settings\n")
            script_lines.append("export DATADIR=%s\n" % str(Path(modpath_full)/pod_settings["CASENAME"]))
            script_lines.append("export OBS_DATA=%s\n" % str(obspath_full/module_dict[module]["alt_name"]))
            script_lines.append("export POD_HOME=%s\n" % module_path_full)
            script_lines.append("export WK_DIR=%s\n" % working_full)
            script_lines.append("export RGB=%s\n" % str(Path(module_dict[module]["mdtf_path"])/"shared"/"rgb"))
            # Each setting becomes an env variable
            for item in pod_settings:
                script_lines.append("export %s=%s\n" % (item, pod_settings[item]))
            for item in module_dict[module]["pod_env_vars"]:
                script_lines.append("export %s=%s\n" % (item, module_dict[module]["pod_env_vars"][item]))
            convention = pod_settings.get("convention","None")
            # Filename will use variable names specific to convention
            flistname = "fieldlist_" + convention + ".jsonc"
            CONV = MDTF_fieldlist(module_dict[module]["mdtf_path"]/"data"/flistname)
            CONV.read()
            # Conventions have some of their own environment variables
            conv_env_vars = CONV.get_env_vars()
            for item in conv_env_vars:
                script_lines.append("export %s=%s\n" % (item, conv_env_vars[item]))
            # Each data variable also becomes an env variable
            # Variable name depends on convention
            for varname in module_dict[module]["pod_varlist"]:
                stnd_name = module_dict[module]["pod_varlist"][varname]["standard_name"]
                if (stnd_name is not None) | (not module_dict[module]["pod_varlist"][varname].get("use_exact_name",False)): # has a convention
                    # Dimensions help with picking correct 3d or 4d name
                    dim_len = len(module_dict[module]["pod_varlist"][varname]["dimensions"])
                    conv_varname = CONV.lookup_by_standard_name(stnd_name,dim_len)
                    if "scalar_coordinates" in module_dict[module]["pod_varlist"][varname]:
                        try:
                            conv_varname += str(module_dict[module]["pod_varlist"][varname]["scalar_coordinates"]["lev"])
                        except KeyError:
                            conv_varname += str(module_dict[module]["pod_varlist"][varname]["scalar_coordinates"]["plev"])
                    script_lines.append("export %s=%s\n" % (varname+"_var",conv_varname))
                    env_basename = Path("%s.%s.%s.nc" % (pod_settings["CASENAME"], conv_varname, module_dict[module]["frequency"]))
                else: # no convention
                    script_lines.append("export %s=%s\n" % (varname+"_var",varname))
                    env_basename = Path("%s.%s.%s.nc" % (pod_settings["CASENAME"], varname, module_dict[module]["frequency"]))
                env_path = modpath_full/Path(pod_settings["CASENAME"])/Path(module_dict[module]["frequency"])/env_basename
                env_var = varname.upper()+"_FILE"
                script_lines.append("export %s=%s\n" % (env_var,env_path))
            # remove unneeded levels for EOF_500hPa. By default use 'lev'
            if "plev" in module_dict[module]["dimensions"] and "lev" in module_dict[module]["dimensions"]:
                pop_var = "plev"
                if "USE_HYBRID_SIGMA" in module_dict[module]["pod_varlist"]:
                    if module_dict[module]["pod_varlist"]["USE_HYBRID_SIGMA"] == 0:
                        pop_var = "lev"
                module_dict[module]["dimensions"].pop(pop_var)
            for dim in module_dict[module]["dimensions"]:
                env_var = dim
                script_lines.append("export %s_coord=%s\n" % (env_var,env_var))

            # Need to activate conda env here since MDTF driver scripts don't do it
            env_name = get_mdtf_env(module, module_dict[module]["runtime"])
            script_lines.append("\nsource $CONDA_SOURCE\nconda activate $CONDA_ENV_ROOT/%s\n" % env_name)

            # Copy html page from module codebase
            index_pod = module_dict[module]["alt_name"] + ".html"
            module_dict[module].update({"index": index_pod})
            src = module_path_full/index_pod
            dst = path_out/index_pod
            mdtf_copy_html(src,dst,pod_settings)

        driver = module_dict[module]["driver_script"]
        if driver.suffix == ".py":
            script_lines.append("python %s\n" % driver)
        else:
            script_lines.append("%s\n" % driver)
        with open(path_script, "w") as script:
            script.writelines(script_lines)
        path_script.chmod(0o775)

    # Get main cmec-driver index.html info
    cmec_index = CMECIndex(workpath)
    cmec_index.read()

    # Execute command scripts
    print("Executing driver scripts")
    for module in module_dict:
        mod_is_pod = module_dict[module]["mod_is_pod"]
        working_dir = module_dict[module]["working_dir"]
        env_script = str(module_dict[module]["env_script"])
        path_out = module_dict[module]["working_dir_full"]
        print("------------------------------------------------------------")
        subprocess.call(["sh",env_script], shell=False)

        # Generate index.html if not available
        # First find index name
        if Path(path_out/"output.json").exists():
            with open(Path(path_out/"output.json")) as output_json:
                results = json.load(output_json)
            index = results.get("index","index.html")
        elif mod_is_pod:
            index = module_dict[module].get("index","index.html")
            mdtf_ps_to_png(path_out/"model"/"PS",path_out/"model",lib.get_conda_root(),lib.get_env_root())
            mdtf_copy_obs(obspath_full,path_out/"obs")
            mdtf_copy_banner(module_dict[module]["mdtf_path"],path_out)
            clear_ps = not(pod_settings.get("save_ps",False))
            clear_nc = not(pod_settings.get("save_nc",False))
            mdtf_file_cleanup(path_out,clear_ps,clear_nc)
        else: 
            index = "index.html"
        result_list = os.listdir(path_out)
        result_list.remove("cmec_run.bash")
        cmec_index.link_results(str(working_dir),str(working_dir/index))

    print("------------------------------------------------------------")
    # Generate cmec-driver navigation page
    cmec_index.write()


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
    parser_inst.add_argument("-clear_conda", action="store_true", default=False)
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
            clear_conda=args.clear_conda)

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
