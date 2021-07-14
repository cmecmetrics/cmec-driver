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
