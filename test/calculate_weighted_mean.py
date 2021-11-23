import numpy as np
import xarray as xr
import argparse
import json

def weighted_mean(input_data_path, var):
    """Returns the temporal and spatial weighted mean for a variable

    Args:
        input_data_path (str): path to the input netCDF
        var (str): name of the variable to average
    """
    data = xr.load_dataset(input_data_path)
    data_weights = np.cos(np.deg2rad(data.lat))
    data_weights.name = "weights"
    weighted_data = data.weighted(data_weights)
    weighted_mean = weighted_data.mean(("time","lon","lat"))
    return float(weighted_mean[var].data)

parser = argparse.ArgumentParser(description="inputs for weighted mean")
parser.add_argument("input", help="netCDF data path")
parser.add_argument("var", help="variable name to average")
parser.add_argument("output", help="output file name")
parser.add_argument("-html", help="html file name", default="")
args = parser.parse_args()

weighted_average = weighted_mean(args.input, args.var)

output_json = {"DIMENSIONS": {}, "RESULTS": {"Global": {}}}
output_json["DIMENSIONS"]["json_structure"] = ["region", "var", "metric"]
output_json["DIMENSIONS"]["metric"] = {"weighted_mean": {"Name": "Spatially weighted temporal mean", "Contact": "none"}}
output_json["DIMENSIONS"]["region"] = {"Global": {}}
output_json["RESULTS"]["Global"][args.var] = {}
output_json["RESULTS"]["Global"][args.var]["weighted_mean"] = weighted_average

with open(args.output, "w") as outfile:
    json.dump(output_json, outfile)

if args.html:
    with open(args.html, "w") as index_html:
        index_html.writelines(["<html>\n<head><title>Test page</title></head>\n<h1>Result</h1>\n</html>"])
