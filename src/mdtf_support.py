"""
"""
from pathlib import Path
import glob
import json
import shutil
import string
import subprocess
import sys
import os

def remove_directory(dir_path):
    """Delete the contents of a directory, then delete the directory.
    Can delete 1 level of sub directories.

    Args:
        dir_path (Path): path to directory to delete.
    """
    if dir_path.exists():
        for item in dir_path.iterdir():
            if item.is_dir():
                for sub_item in item.iterdir():
                    sub_item.unlink()
                item.rmdir()
            else:
                item.unlink()
        dir_path.rmdir()

class MDTF_fieldlist():
    def __init__(self,fpath):
        self.fieldlist_path = str(fpath)
        self.fields = ""
        self.vars = ""
        self.env_vars = {}

    def read(self):
        """Load the convention file contents and save key values.
        """
        try:
            with open(self.fieldlist_path,"r") as fieldlist_file:
                fields = json.loads(
                    "\n".join(row.split("//",1)[0] for row in fieldlist_file \
                    if not row.lstrip().startswith("//")))
            self.no_convention = False
        except IOError:
            print("Fieldlist not found. Setting convention to 'None'")
            fields = {"variables": {},"coords": {}}
            self.no_convention = True
        self.fields = fields
        self.env_vars = fields["env_vars"]
        self.vars = fields["variables"]
        if "plev" in self.fields["coords"]:
            self.lev_coord = "plev"
        elif "lev" in self.fields["coords"]:
            self.lev_coord = "lev"

    def get_standard_name(self,varname):
        """Return the standard name field for a variable.
        """
        if self.no_convention:
            return None
        # Split off levels like "1000" or "850"
        if varname[-4:].isnumeric():
            varname = varname[0:-4]
        if varname[-3:].isnumeric():
            varname = varname[0:-3]
        return self.vars[varname].get("standard_name",None)

    def lookup_by_standard_name(self,standard_name,ndims):
        """Return the variable name from a convention based on the standard name.
        """
        def lookup_function(self,standard_name):
            found = ""
            for item in self.vars:
                if self.vars[item].get("standard_name","") == standard_name:
                    if ("scalar_coord_templates" in self.vars[item]) and (ndims != 4):
                        found = self.vars[item]["scalar_coord_templates"][self.lev_coord].format(value = "")
                    else:
                        found = item
            return found

        if self.no_convention:
            return None
        found = lookup_function(self,standard_name)
        # If the correct precipitation variable name doesn't exist in this
        # convention, swap for the variable that is. No units conversions are done.
        if found == "" and standard_name == "precipitation_rate":
            found = lookup_function(self,"precipitation_flux")
            print("\nWARNING: POD calls for precipitation_rate.\nprecipitation_flux variable will be used in place of precipitation_rate WITH NO UNITS CONVERSION!\n")
        elif found == "" and standard_name == "precipitation_flux":
            found = lookup_function(self,"precipitation_rate")
            print("\nWARNING: POD calls for precipitation_flux.\nprecipitation_rate variable will be used in place of precipitation_flux WITH NO UNITS CONVERSION!\n")
        return found

    def get_env_vars(self):
        return self.env_vars

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

def mdtf_copy_html(src,dst,pod_settings):
    """Copy and fill out the html template from the diagnostic codebase.
    Find and copy any other  html files in the code directory."""
    html_lines = []
    with open(src,"r") as f:
        lines = f.readlines()
    for line in lines:
        for item in pod_settings:
            if "{{%s}}" % item in line:
                line = line.replace("{{%s}}" % item,pod_settings[item])
        html_lines.append(line)
    with open(dst,"w") as f:
        f.writelines(html_lines)
    # Copy other html files in folder
    html_files = []
    src_dir = Path(src).parents[0]
    dst_dir = Path(dst).parents[0]
    for item in glob.glob(str(src_dir/'*html')):
        if Path(item).name != src.name:
            html_files.append(item)
    html_files += glob.glob(str(src_dir/'**'/'*html'))
    for item in html_files:
        copy_from = Path(item).relative_to(src_dir)
        if len(copy_from.parents) > 1:
            (dst_dir/copy_from.parents[0]).mkdir(exist_ok=True)
            shutil.copy2(item,dst_dir/copy_from.parents[0])
        else:
            shutil.copy2(item,dst_dir)

def mdtf_ps_to_png(src_dir,dst_dir,conda_source,env_root):
    """Convert PS to PNG files for html page and move files to
    appropriate folder.
    """
    print("Converting figures to png.")
    in_image_list = []
    ext_list = (".ps", ".PS", ".eps", ".EPS", ".pdf", ".PDF")
    file_list = os.listdir(src_dir)
    for ext in ext_list:
        in_image_list.extend(glob.glob(str(Path(src_dir)/("*"+ext))))

    for im_in in in_image_list:
        # Use gs command in MDTF base environment to convert figure types
        image_base = os.path.splitext(im_in)[0]
        im_out = image_base+"_MDTF_TEMP_%d.png"
        cmd = "source {0} && conda activate {1}/_MDTF_base && gs -dSAFER -dBATCH -dNOPAUSE -dEPSCrop -r150 -sDEVICE=png16m -dTextAlphaBits=4 -dGraphicsAlphaBits=4 -sOutputFile={2} {3}".format(conda_source,env_root,im_out,im_in)
        subprocess.run(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
        out_images = [f for f in os.listdir(src_dir) if (os.path.basename(image_base) + "_MDTF_TEMP_" in f) and (f.endswith("png"))]
        # Clean up figure names and renumber when multiple figures generated
        if len(out_images) == 1:
            (src_dir/out_images[0]).rename(image_base+".png")
        else:
            for im_num in range(len(out_images)):
                src = image_base+"_MDTF_TEMP_{0}.png".format(im_num+1)
                dst = image_base + "-{0}.png".format(im_num)
                Path(src).rename(dst)

    # Copy bitmap images to dst
    ext_list = ('.png','.gif','.jpg','.jgep')
    file_list = os.listdir(src_dir)
    move_list = [f for f in file_list if f.endswith(ext_list)]
    for f in src_dir.iterdir():
        if str(f).endswith(ext_list):
            cmd = "mv {0} {1}".format(str(f),str(dst_dir/f.name))
            subprocess.run(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)

def mdtf_rename_img(varlist,conv,img_dir):
    """Rename figure files to use variable names from settings file,
    not conventions."""
    for f in img_dir.iterdir():
        print(f)
        f_name = str(f.name)
        for pod_var in varlist:
            standard_name = varlist[pod_var]["standard_name"]
            dim_len = len(varlist[pod_var]["dimensions"])
            conv_var = conv.lookup_by_standard_name(standard_name,dim_len)
            if "scalar_coordinates" in varlist[pod_var]:
                try:
                    conv_var += str(varlist[pod_var]["scalar_coordinates"]["lev"])
                except KeyError:
                    conv_var += str(varlist[pod_var]["scalar_coordinates"]["plev"])
            print(conv_var)
            if conv_var in f_name:
                f_new = img_dir/f_name.replace(conv_var,pod_var)
                f.rename(f_new)

def mdtf_copy_obs(obs_dir,wk_dir):
    """Copy obs images to output folder."""
    print("Copying obs figures.")
    ext_list = ('.png','.gif','.jpg','.jgep')
    for item in obs_dir.iterdir():
        if str(item).endswith(ext_list):
            src = item
            dst = wk_dir/str(item.name)
            shutil.copy2(str(src),str(dst))

def mdtf_copy_banner(mdtf_path,wk_dir):
    """Copy the banner image."""
    banner_src = Path(mdtf_path)/"src"/"html"/"mdtf_diag_banner.png"
    banner_dst = wk_dir.parents[0]/"mdtf_diag_banner.png"
    if not banner_dst.exists():
        print("Copying MDTF banner image.")
        shutil.copy2(str(banner_src),str(banner_dst))

def mdtf_file_cleanup(wk_dir,clear_ps,clear_nc):
    """Delete PS and netCDF if requested."""
    if clear_ps:
        print("Deleting postscript images.")
        ps_dir = wk_dir/"model"/"PS"
        remove_directory(ps_dir)
    if clear_nc:
        print("Deleting intermediate netCDF files.")
        nc_dir = wk_dir/"model"/"netcdf"
        remove_directory(nc_dir)
