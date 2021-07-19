"""
"""
from pathlib import Path
import glob
import json
import string
import subprocess
import sys
import os

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
    """Copy and fill out the html template from the diagnostic codebase."""
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
    # See if there are any other html files to copy
    result_list = os.listdir(src.parents[0])
    if "htmls" in result_list:
        src2 = str(src.parents[0]/"htmls")
        dst2 = str(dst.parents[0])
        subprocess.call(["cp",src2,dst2],shell=False)

def mdtf_ps_to_png(src_dir,dst_dir,conda_source,env_root):
    """Convert PS to PNG files for html page and move files to
    appropriate folder.
    """
    in_image_list = []
    ext_list = (".ps", ".PS", ".eps", ".EPS", ".pdf", ".PDF")
    file_list = os.listdir(src_dir)
    for file in file_list:
        if file.endswith(ext_list):
            image_name = os.path.join(src_dir,file)
            in_image_list.append(image_name)

    for im_in in in_image_list:
        # Use gs command in MDTF base environment to convert figure types
        image_base = os.path.splitext(im_in)[0]
        im_out = image_base+"_MDTF_TEMP_%d.png"
        cmd = "source {0} && conda activate {1}/_MDTF_base && gs -dSAFER -dBATCH -dNOPAUSE -dEPSCrop -r150 -sDEVICE=png16m -dTextAlphaBits=4 -dGraphicsAlphaBits=4 -sOutputFile={2} {3}".format(conda_source,env_root,im_out,im_in)
        os.system(cmd)
        out_images = [f for f in os.listdir(src_dir) if (os.path.basename(image_base) + "_MDTF_TEMP_" in f) and (f.endswith("png"))]
        # Clean up figure names and renumber when multiple figures generated
        if len(out_images) == 1:
            print(out_images[0])
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
        os.system(cmd)

def mdtf_copy_obs():
    """Copy obs data to output folder."""
    pass

def mdtf_file_cleanup(wk_dir,clear_ps=True,clear_nc=True):
    """Delete PS and netCDF if requested."""
    if clear_ps:
        pass
