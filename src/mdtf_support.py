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

class MDTF_fieldlist():
    def __init__(self,fpath):
        self.fieldlist_path = str(fpath)
        self.fields = ""
        self.vars = ""

    def read(self):
        with open(self.fieldlist_path,"r") as fieldlist_file:
            fields = json.loads(
                "\n".join(row.split("//",1)[0] for row in fieldlist_file \
                if not row.lstrip().startswith("//")))
        self.fields = fields
        self.vars = fields["variables"]

    def get_standard_name(self,varname):
        #TODO - figure how how much of string is numeric, ie for levels like 1000
        if varname[-3:].isnumeric():
            varname = varname[0:-3]
        return self.vars[varname].get("standard_name",None)

    def lookup_by_standard_name(self,standard_name):
        for item in self.vars:
            if self.vars[item].get("standard_name","") == standard_name:
                return item

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
    fieldlist_path = Path(mPath).parents[1]/Path("data")
    fieldlist_file = "fieldlist_" + convention + ".jsonc"
    with open(fieldlist_path/Path("fieldlist_CMIP.jsonc"), "r") as fieldlist:
        flist_cmip = json.loads("\n".join(row for row in fieldlist if (not row.lstrip().startswith("//")) and (row.find(", //") < 0)))["variables"]

    try:
        with open(fieldlist_path/fieldlist_file, "r") as fieldlist:
            flist = json.loads("\n".join(row for row in fieldlist if not (row.lstrip().startswith("//")) and (row.find(", //") < 0)))["variables"]
    except FileNotFoundError:
        raise CMECError("Fieldlist for convention " + convention + " not found.")

    standard_name = flist_cmip[varname]["standard_name"]
    for model_var in flist:
        if flist[model_var]["standard_name"] == standard_name:
            return model_var

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
        #os.system(cmd)
        print("Converting figures to png.")
        subprocess.run(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
        out_images = [f for f in os.listdir(src_dir) if (os.path.basename(image_base) + "_MDTF_TEMP_" in f) and (f.endswith("png"))]
        # Clean up figure names and renumber when multiple figures generated
        if len(out_images) == 1:
            os.rename(os.path.join(src_dir,out_images[0]), image_base + ".png")
        else:
            for im_num in range(len(out_images)):
                os.rename(image_base + "_MDTF_TEMP_{0}.png".format(im_num+1),
                    image_base + "-{0}.png".format(im_num))

    # Copy bitmap images to dst
    ext_list = ('.png','.gif','.jpg','.jgep')
    file_list = os.listdir(src_dir)
    move_list = [f for f in file_list if f.endswith(ext_list)]
    for f in move_list:
        cmd = "mv {0} {1}".format(os.path.join(src_dir,f),os.path.join(dst_dir,f))
        subprocess.run(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)

def mdtf_copy_obs(obs_dir,wk_dir):
    """Copy obs images to output folder."""
    ext_list = ('.png','.gif','.jpg','.jgep')
    for item in os.listdir(obs_dir):
        if item.endswith(ext_list):
            shutil.copy2(os.path.join(str(obs_dir),item),str(wk_dir/item))

def mdtf_file_cleanup(wk_dir,clear_ps,clear_nc):
    """Delete PS and netCDF if requested."""
    if clear_ps:
        ps_dir = str(wk_dir/"model"/"PS")
        if os.path.exists(ps_dir):
            for item in os.listdir(ps_dir):
                os.remove(os.path.join(ps_dir,item))
            os.rmdir(ps_dir)
    if clear_nc:
        nc_dir = str(wk_dir/"model"/"netcdf")
        if os.path.exists(nc_dir):
            for item in os.listdir(nc_dir):
                os.remove(os.path.join(nc_dir,item))
            os.rmdir(nc_dir)
