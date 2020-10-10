///////////////////////////////////////////////////////////////////////////////
///
///	\file    pmp-to-cmec.cpp
///	\author  Paul Ullrich
///	\version October 9, 2020
///
///	<remarks>
///		Copyright (c) 2020 Paul Ullrich 
///	
///		Distributed under the BSD 3-Clause License.
///		(See accompanying file LICENSE)
///	</remarks>

#include <cstdio>
#include <cstdlib>
#include <unistd.h>
#include <pwd.h>

#include "contrib/json.hpp"
#include "filesystem_path.h"

#include "Exception.h"
#include "Terminal.h"

///////////////////////////////////////////////////////////////////////////////

void RecurseDimensionValuesFromRESULTS(
	const std::vector<std::string> & vecInvalidStrings,
	const nlohmann::json & js,
	std::vector< std::vector<std::string> > & vecDimensionValues,
	size_t sLevel
) {
	for (auto it = js.begin(); it != js.end(); it++) {
		std::string strKey = it.key();

		// Check key against list of keys to avoid
		bool fInvalidString =
			std::find(
				vecInvalidStrings.begin(),
				vecInvalidStrings.end(),
				strKey) != vecInvalidStrings.end();
		if (fInvalidString) {
			continue;
		}

		// Change blank keys to "Unspecified"
		if (strKey == "") {
			strKey = "Unspecified";
		}

		// Check if this is already in the array of dimension names
		bool fExists =
			std::find(
				vecDimensionValues[sLevel].begin(),
				vecDimensionValues[sLevel].end(),
				strKey) != vecDimensionValues[sLevel].end();

		if (sLevel != vecDimensionValues.size()-1) {
			RecurseDimensionValuesFromRESULTS(
				vecInvalidStrings,
				*it,
				vecDimensionValues,
				sLevel+1);
		}

		if (fExists) {
			continue;
		}

		vecDimensionValues[sLevel].push_back(strKey);
	}
}

///////////////////////////////////////////////////////////////////////////////

void RecursivelyCopyRESULTS(
	const std::vector<std::string> & vecInvalidStrings,
	const std::vector< std::vector<std::string> > & vecDimensionValues,
	bool fBlank,
	const nlohmann::json & jsIn,
	nlohmann::json & jsOut,
	size_t sLevel
) {
	// Generate a blank RESULTS panel
	if (fBlank) {
		if (sLevel == vecDimensionValues.size()) {
			jsOut = -999.0;
		} else {
			for (size_t s = 0; s < vecDimensionValues[sLevel].size(); s++) {
				jsOut[vecDimensionValues[sLevel][s]] = nlohmann::json::object();

				RecursivelyCopyRESULTS(
					vecInvalidStrings,
					vecDimensionValues,
					fBlank,
					jsIn,
					jsOut[vecDimensionValues[sLevel][s]],
					sLevel+1);
			}
		}
		return;
	}

	// Fill in RESULTS from the file
	std::vector<bool> vecValuesFound(vecDimensionValues[sLevel].size(), false);

	for (auto it = jsIn.begin(); it != jsIn.end(); it++) {
		std::string strKey = it.key();

		std::cout << strKey << std::endl;

		// Check key against list of keys to avoid
		bool fInvalidString =
			std::find(
				vecInvalidStrings.begin(),
				vecInvalidStrings.end(),
				strKey) != vecInvalidStrings.end();
		if (fInvalidString) {
			continue;
		}

		// Change blank keys to "Unspecified"
		if (strKey == "") {
			strKey = "Unspecified";
		}

		// Identify this value as found
		for (size_t v = 0; v <= vecDimensionValues[sLevel].size(); v++) {
			if (v == vecDimensionValues[sLevel].size()) {
				_EXCEPTIONT("Logic Error");
			}
			if (strKey == vecDimensionValues[sLevel][v]) {
				vecValuesFound[v] = true;
				break;
			}
		}

		// Recursively copy
		if (it->is_object()) {
			jsOut[strKey] = nlohmann::json::object();

			RecursivelyCopyRESULTS(
				vecInvalidStrings,
				vecDimensionValues,
				false,
				*it,
				jsOut[strKey],
				sLevel+1);

		} else if (it->is_string()) {
			jsOut[strKey] = std::stod(std::string(it.value()));
		} else {
			jsOut[strKey] = *it;
		}
	}

	// Fill in blanks
	for (size_t s = 0; s < vecValuesFound.size(); s++) {
		if (!vecValuesFound[s]) {
			RecursivelyCopyRESULTS(
				vecInvalidStrings,
				vecDimensionValues,
				true,
				jsIn,
				jsOut[vecDimensionValues[sLevel][s]],
				sLevel+1);
		}
	}
}

///////////////////////////////////////////////////////////////////////////////

///	<summary>
///		Convert a PMP style metrics JSON file to a CMEC style JSON file.
///	</summary>
void PMPtoCMECJSON(
	const std::string & strPMPfile,
	const std::string & strCMECfile
) {
	std::vector< std::string > vecDimensionNames;
	std::vector< std::vector<std::string> > vecDimensionValues;

	// List of strings to not parse in RESULTS
	std::vector<std::string> vecInvalidStrings;
	vecInvalidStrings.push_back("units");
	vecInvalidStrings.push_back("SimulationDescription");
	vecInvalidStrings.push_back("InputClimatologyFileName");
	vecInvalidStrings.push_back("InputClimatologyMD5");
	vecInvalidStrings.push_back("InputRegionFileName");
	vecInvalidStrings.push_back("InputRegionMD5");
	vecInvalidStrings.push_back("source");

	// Input stream
	std::ifstream ifs(strPMPfile);
	if (!ifs.is_open()) {
		_EXCEPTION1("Unable to open PMP JSON file \"%s\"",
			strPMPfile.c_str());
	}

	// Output stream
	std::ofstream ofs(strCMECfile, std::ios::out);
	if (!ofs.is_open()) {
		_EXCEPTION1("Unable to open file \"%s\" for writing", strCMECfile.c_str());
	}

	// Parse into a PMP JSON object
	nlohmann::json jpmp;
	try {
		jpmp = nlohmann::json::parse(ifs);
	} catch (nlohmann::json::parse_error& e) {
		_EXCEPTION3("Malformed PMP JSON file "
			"%s (%i) at byte position %i",
			e.what(), e.id, e.byte);
	}

	// Get "json_structure" from PMP file
	auto itjstruct = jpmp.find("json_structure");
	if (itjstruct == jpmp.end()) {
		_EXCEPTION1("Malformed PMP JSON file \"%s\" (missing top level \"json_structure\" key)",
			strPMPfile.c_str());
	}

	// Get "RESULTS" from PMP file
	auto itjresults = jpmp.find("RESULTS");
	if (itjresults == jpmp.end()) {
		_EXCEPTION1("Malformed PMP JSON file \"%s\" (missing top level \"RESULTS\" key)",
			strPMPfile.c_str());
	}

	// Output JSON object
	nlohmann::json jcmec;

	jcmec["SCHEMA"]["name"] = "CMEC";
	jcmec["SCHEMA"]["version"] = "v1";
	jcmec["SCHEMA"]["package"] = "PMP";

	// Copy over additional keys
	for (auto itkey = jpmp.begin(); itkey != jpmp.end(); itkey++) {
		if ((itkey.key() != "RESULTS") && (itkey.key() != "json_structure")) {
			jcmec[itkey.key()] = itkey.value();
		}
	}

	// Dimensions
	auto & jcmecdimarr = jcmec["DIMENSIONS"]["json_structure"] = nlohmann::json::array();
	for (auto itdim = itjstruct->begin(); itdim != itjstruct->end(); itdim++) {
		vecDimensionNames.push_back(itdim.value());
		jcmecdimarr.push_back(itdim.value());
	}

	// Recursively examine RESULTS to build dimension names
	vecDimensionValues.resize(vecDimensionNames.size());
	RecurseDimensionValuesFromRESULTS(
		vecInvalidStrings,
		*itjresults,
		vecDimensionValues,
		0);

	auto & jdims = jcmec["DIMENSIONS"]["dimensions"];
	for (int s = 0; s < vecDimensionValues.size(); s++) {
		jdims[vecDimensionNames[s]] = nlohmann::json::object();
		if (vecDimensionNames[s] == "statistic") {
			jdims[vecDimensionNames[s]]["indices"] = nlohmann::json::array();
			for (int v = 0; v < vecDimensionValues[s].size(); v++) {
				jdims[vecDimensionNames[s]]["indices"].push_back(vecDimensionValues[s][v]);
			}
		} else {
			for (int v = 0; v < vecDimensionValues[s].size(); v++) {
				jdims[vecDimensionNames[s]][vecDimensionValues[s][v]] = nlohmann::json::object();
			}
		}
	}

	// Recursively copy RESULTS
	RecursivelyCopyRESULTS(
		vecInvalidStrings,
		vecDimensionValues,
		false,
		*itjresults,
		jcmec["RESULTS"],
		0);

	// Write to file
	ofs << std::setw(4) << jcmec << std::endl;
	ofs.close();
}

///////////////////////////////////////////////////////////////////////////////

int main(int argc, char **argv) {

	try {

	// Executable
	std::string strExecutable = argv[0];

	// Arguments
	std::vector<std::string> vecArg;
	for (int c = 1; c < argc; c++) {
		vecArg.push_back(argv[c]);
	}

	// Only two arguments allowed
	if (vecArg.size() != 2) {
		printf("Usage: %s <PMP json file> <CMEC json file>\n", strExecutable.c_str());
		return 1;
	}

	// Call the converter
	PMPtoCMECJSON(vecArg[0], vecArg[1]);

	// Catch exceptions
	} catch(Exception & e) {
		std::cout << std::endl << e.ToString() << std::endl;
		return 1;

	} catch(std::runtime_error & e) {
		std::cout << std::endl << e.what() << std::endl;
		return 1;

	} catch(...) {
		return 1;
	}

	return 0;
}
 
///////////////////////////////////////////////////////////////////////////////

