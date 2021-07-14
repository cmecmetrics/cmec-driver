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

version = "20210617"
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
        if mod_is_pod:
            path_out_tmp = path_out / "model" / "netcdf"
            path_out_tmp.mkdir(parents=True)
            path_out_tmp = path_out / "model" / "PS"
            path_out_tmp.mkdir(parents=True)
            path_out_tmp = path_out / "obs"
            path_out_tmp.mkdir(parents=True)

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
                # copy html page
                index_pod = module + ".html"
                src = module_path_full / index_pod
                dst = path_working_dir / index_pod
                html_lines = []
                with open(src,"r") as f:
                    lines = f.readlines()
                for line in lines:
                    # TODO see if there's other settings that need to be popped in
                    # see https://github.com/NOAA-GFDL/MDTF-diagnostics/blob/d00538dbd39740baab905121508bbe87cc52d716/src/output_manager.py#L67
                    if "{{CASENAME}}" in line:
                        line = line.replace("{{CASENAME}}",pod_settings["CASENAME"])
                    html_lines.append(line)
                with open(dst,"w") as f:
                    f.writelines(html_lines)
                    # TODO copy obs data into correct locations
                    # TODO also ref other tasks in https://github.com/NOAA-GFDL/MDTF-diagnostics/blob/d00538dbd39740baab905121508bbe87cc52d716/src/output_manager.py#L199
            if driver.suffix == ".py":
                script_lines.append("python %s\n" % driver)
            else:
                script_lines.append("%s\n" % driver)
            script.writelines(script_lines)
        os.system("chmod u+x " + str(path_script))

    # Get main cmec-driver index.html info
    cmec_index = CMECIndex(workpath)
    cmec_index.read()

    # Execute command scripts
    print("Executing driver scripts")
    for env_script, working_dir in zip(env_scripts, working_dir_list):
        print("------------------------------------------------------------")
        subprocess.call(["sh",env_script], shell=False)
        # Generate index.html if not available:
        result_list = os.listdir(workpath / working_dir)
        result_list.remove("cmec_run.bash")
        if Path(workpath / working_dir / "output.json").exists():
            with open(Path(workpath / working_dir / "output.json")) as output_json:
                results = json.load(output_json)
            index = results["index"]
        elif mod_is_pod:
            index = index_pod
            # TODO: convert PS images to PNG e.g. https://github.com/NOAA-GFDL/MDTF-diagnostics/blob/d00538dbd39740baab905121508bbe87cc52d716/src/output_manager.py#L95
        else: 
            index = "index.html"
        if not (index in result_list) and not mod_is_pod:
            print("Generating default index.html")
            # Generate default index
            html_text=['<html>\n',
                '<body>',
                '<head><title>CMEC Driver Results</title></head>\n',
                '<h1>{0} Results</h1>\n'.format(str(working_dir))]
            for item in result_list:
                if item.lower().endswith(('.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.gif')):
                    html_text.append('<p><a href="{0}" target="_blank" alt={0}><img src="{0}" width="647" alt="{0}"></a></p>\n'.format(item))
                else:    
                    html_text.append('<br><a href="{0}" target="_blank">{0}</a>\n'.format(item))
            html_text.append('</html>')
            with open(workpath / working_dir / index, "w") as index_html:
                index_html.writelines(html_text)
        cmec_index.link_results(str(working_dir),str(working_dir / index))
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
