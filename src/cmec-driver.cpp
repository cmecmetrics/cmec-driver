///////////////////////////////////////////////////////////////////////////////
///
///	\file    cmec-driver.cpp
///	\author  Paul Ullrich
///	\version June 19, 2020
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

#include <map>
#include <string>
#include <vector>
#include <iostream>
#include <iomanip>
#include <fstream>
#include <cctype>

#include "contrib/json.hpp"
#include "filesystem_path.h"

#include "Announce.h"
#include "Exception.h"

///////////////////////////////////////////////////////////////////////////////

static const char * g_szVersion = "20200723";

///////////////////////////////////////////////////////////////////////////////

typedef std::map<std::string, int> CommandLineFlagSpec;

typedef std::map<std::string, std::vector<std::string> > CommandLineFlagMap;

typedef std::vector<std::string> CommandLineArgVector;

std::string ParseCommandLine(
	int ibegin,
	int iend,
	char ** argv,
	const CommandLineFlagSpec & spec,
	CommandLineFlagMap & mapFlags,
	CommandLineArgVector & vecArg
) {
	// Flags occur before raw arguments
	bool fReadingFlags = true;

	// Loop through all command line arguments
	for (int c = ibegin; c < iend; c++) {
		_ASSERT(strlen(argv[c]) >= 1);

		// Handle flags
		if (argv[c][0] == '-') {
			if (!fReadingFlags) {
				return std::string("Error: Malformed argument \"") + std::string(argv[c]) + std::string("\"");
			}
			if (strlen(argv[c]) == 1) {
				continue;
			}
			std::string strFlag = argv[c] + 1;
			
			CommandLineFlagSpec::const_iterator iterSpec = spec.find(strFlag);
			if (iterSpec == spec.end()) {
				return std::string("Error: Invalid flag \"") + strFlag + std::string("\"");
			}

			CommandLineFlagMap::iterator iterFlags = mapFlags.find(strFlag);
			if (iterFlags != mapFlags.end()) {
				return std::string("Error: Duplicated flag \"") + strFlag + std::string("\"");
			}

			int nargs = iterSpec->second;
			if (c + nargs >= iend) {
				return std::string("Error: Insufficient arguments for \"")
					+ strFlag + std::string("\"");
			}

			std::vector<std::string> vecFlagArg;
			for (int d = 0; d < nargs; d++) {
				_ASSERT(strlen(argv[c+d]) >= 1);
				if (argv[c+d+1][0] == '-') {
					return std::string("Error: Invalid arguments for \"")
						+ strFlag + std::string("\"");
				}
				vecFlagArg.push_back(argv[c+d+1]);
			}

			mapFlags.insert(CommandLineFlagMap::value_type(strFlag, vecFlagArg));

			c += nargs;

		// Handle raw arguments
		} else {
			if (fReadingFlags) {
				fReadingFlags = false;
			}

			vecArg.push_back(argv[c]);
		}
	}

	return std::string("");
}

///////////////////////////////////////////////////////////////////////////////

class CMECLibrary {

public:
	///	<summary>
	///		A map from module names to corresponding paths.
	///	</summary>
	typedef std::map<std::string, filesystem::path> ModuleNamePathMap;

	///	<summary>
	///		A const_iterator into the map.
	///	</summary>
	typedef ModuleNamePathMap::const_iterator const_iterator;

public:
	///	<summary>
	///		Constructor.
	///	</summary>
	CMECLibrary() {
	}

	///	<summary>
	///		Clear the library.
	///	</summary>
	void Clear() {
		m_path = filesystem::path();
		m_mapModulePaths.clear();
		m_jlib.clear();
	}

	///	<summary>
	///		Initialize the CMEC library path.
	///	</summary>
	void InitializePath() {
		// Search for $HOME/.autodataman
		char * homedir = getenv("HOME");

		if (homedir != NULL) {
			filesystem::path pathNamelist(homedir);
			if (!pathNamelist.exists()) {
				_EXCEPTIONT("Environment variable $HOME points to an invalid home directory path\n");
			}
			m_path = pathNamelist/filesystem::path(".cmeclibrary");
			return;
		}

		// Search for <pwd>/.autodataman
		uid_t uid = getuid();
		struct passwd *pw = getpwuid(uid);

		if (pw == NULL) {
			_EXCEPTIONT("Unable to identify path for .cmeclibrary");
		}

		filesystem::path pathNamelist(pw->pw_dir);
		if (!pathNamelist.exists()) {
			_EXCEPTIONT("pwd points to an invalid home directory path");
		}
		m_path = pathNamelist/filesystem::path(".cmeclibrary");
	}

	///	<summary>
	///		Load the library from a file, or intiialize an empty library
	///		if the library file doesn't exist.
	///	</summary>
	void Read() {

		// Clear the library
		Clear();

		// Initialize the path
		InitializePath();

		// Load the library
		std::ifstream iflib(m_path.str());
		if (!iflib.is_open()) {

			// Create the CMEC library
			Announce("CMEC library not found; creating new library");
			
			// If the library does not exist, create it
			std::ofstream oflib(m_path.str());
			if (!oflib.is_open()) {
				_EXCEPTION1("Unable to open \"%s\" for writing",
					m_path.str().c_str());
			}
			nlohmann::json jlib;
			jlib["version"] = g_szVersion;
			jlib["cmec-driver"] = nlohmann::json::value_t::object;
			jlib["modules"] = nlohmann::json::value_t::object;
			oflib << jlib;

			oflib.close();

			iflib.open(m_path.str());
			if (!iflib.is_open()) {
				_EXCEPTION1("Unable to reopen \"%s\" for reading after creation",
					m_path.str().c_str());
			}
		}


		// Parse the library
		{
			try {
				m_jlib = nlohmann::json::parse(iflib);
			} catch (nlohmann::json::parse_error& e) {
				_EXCEPTION3("Malformed CMEC library file "
					"%s (%i) at byte position %i",
					e.what(), e.id, e.byte);
			}

			auto itd = m_jlib.find("cmec-driver");
			if (itd == m_jlib.end()) {
				_EXCEPTIONT("Malformed CMEC library file missing key \"cmec-driver\"");
			}
			if (!itd->is_object()) {
				_EXCEPTIONT("Malformed CMEC library file \"cmec-driver\" is not of type object");
			}

			auto itv = m_jlib.find("version");
			if (itv == m_jlib.end()) {
				_EXCEPTIONT("Malformed CMEC library file missing key \"version\"");
			}
			if (!itv->is_string()) {
				_EXCEPTIONT("Malformed CMEC library file \"version\" is not of type string");
			}

			auto itm = m_jlib.find("modules");
			if (itm == m_jlib.end()) {
				_EXCEPTIONT("Malformed CMEC library file missing key \"modules\"");
			}
			if (!itm->is_object()) {
				_EXCEPTIONT("Malformed CMEC library file \"modules\" is not of type object");
			}

			std::string strLibVersion = *itv;
			std::string strDriverVersion = g_szVersion;
			if (strDriverVersion < strLibVersion) {
				_EXCEPTION2("CMEC library file version \"%s\" is greater than driver version \"%s\"",
					strLibVersion.c_str(), g_szVersion);
			}

			// Load modules
			nlohmann::json jmodules = *itm;
			for (auto itmod = jmodules.begin(); itmod != jmodules.end(); itmod++) {
				if (!itmod->is_string()) {
					_EXCEPTIONT("Malformed CMEC library file: an entry of the \"modules\" array is not of type string");
				}
				Insert(itmod.key(), filesystem::path(itmod.value()));
			}
		}
	}

	///	<summary>
	///		Write the library to a file.
	///	</summary>
	void Write() {

		// Initialize the path
		InitializePath();

		// Open output stream
		std::ofstream oflib(m_path.str());
		if (!oflib.is_open()) {
			_EXCEPTION1("Unable to open \"%s\" for writing",
				m_path.str().c_str());
		}

		// Output the JSON structure to the file
		oflib << m_jlib;
	}

	///	<summary>
	///		Insert a new path into the system.
	///	</summary>
	bool Insert(
		const std::string & strModuleName,
		const filesystem::path & path
	) {
		// Verify module doesn't exist already
		if (m_mapModulePaths.find(strModuleName) != m_mapModulePaths.end()) {
			Announce("\nERROR: Module already exists in library; "
				"if path has changed first run \"unregister %s\"",
				strModuleName.c_str());

			return false;
		}

		// Insert module
		m_mapModulePaths.insert(
			std::pair<std::string, filesystem::path>(
				strModuleName, path));

		m_jlib["modules"][strModuleName] = path.str();

		return true;
	}

	///	<summary>
	///		Remove a module from the library.
	///	</summary>
	bool Remove(
		const std::string & strModuleName
	) {
		auto it = m_mapModulePaths.find(strModuleName);
		if (it == m_mapModulePaths.end()) {
			Announce("\nERROR: Module \"%s\" not found in library",
				strModuleName.c_str());
			return false;
		}

		nlohmann::json jmodules = m_jlib["modules"];
		auto itmod = jmodules.find(strModuleName);
		if (itmod == jmodules.end()) {
			_EXCEPTIONT("Logic error:  Module appears in map but not in json representation");
		}

		// Remove from map and json
		m_mapModulePaths.erase(it);
		jmodules.erase(itmod);

		return true;
	}

public:
	///	<summary>
	///		Number of modules in this library.
	///	</summary>
	size_t size() const {
		return m_mapModulePaths.size();
	}

	///	<summary>
	///		Constant iterator into module map.
	///	</summary>
	ModuleNamePathMap::const_iterator begin() const {
		return m_mapModulePaths.begin();
	}

	///	<summary>
	///		Constant iterator into module map.
	///	</summary>
	ModuleNamePathMap::const_iterator end() const {
		return m_mapModulePaths.end();
	}

protected:
	///	<summary>
	///		Path to the CMEC library.
	///	</summary>
	filesystem::path m_path;

	///	<summary>
	///		Map of module names to module paths.
	///	</summary>
	ModuleNamePathMap m_mapModulePaths;

	///	<summary>
	///		JSON file representation of the CMEC library.
	///	</summary>
	nlohmann::json m_jlib;
};

///////////////////////////////////////////////////////////////////////////////

void validate_cmec_json(
	nlohmann::json & jcmec
) {
	auto itm = jcmec.find("module");
	if (itm == jcmec.end()) {
		_EXCEPTIONT("Malformed CMEC library file missing key \"module\"");
	}
	if (!itm->is_object()) {
		_EXCEPTIONT("Malformed CMEC library file \"module\" is not of type object");
	}

	nlohmann::json jmodule = *itm;
	auto itmn = jmodule.find("name");
	if (itmn == jmodule.end()) {
		_EXCEPTIONT("Malformed CMEC library file missing key \"module::name\"");
	}
	if (!itmn->is_string()) {
		_EXCEPTIONT("Malformed CMEC library file \"module::name\" is not of type string");
	}

	auto itml = jmodule.find("long_name");
	if (itml == jmodule.end()) {
		_EXCEPTIONT("Malformed CMEC library file missing key \"module::long_name\"");
	}
	if (!itml->is_string()) {
		_EXCEPTIONT("Malformed CMEC library file \"module::long_name\" is not of type string");
	}

	auto itc = jcmec.find("contents");
	if (itc == jcmec.end()) {
		_EXCEPTIONT("Malformed CMEC library file missing key \"contents\"");
	}
	if (!itc->is_object()) {
		_EXCEPTIONT("Malformed CMEC library file \"contents\" is not of type object");
	}
}

///////////////////////////////////////////////////////////////////////////////

///	<summary>
///		Register the specified module directory.
///	</summary>
int cmec_register(
	const std::string & strDirectory
) {
	AnnounceStartBlock("Registering \"%s\"", strDirectory.c_str());

	// Check path for cmec.json
	Announce("Validating cmec.json");

	filesystem::path pathModule(strDirectory);
	filesystem::path pathCMECjson = pathModule / filesystem::path("cmec.json");
	std::ifstream ifCMECjson(pathCMECjson.str());
	if (!ifCMECjson.is_open()) {
		_EXCEPTION1("Unable to open \"%s\"", pathCMECjson.str().c_str());
	}

	// Parse the CMEC json
	nlohmann::json jcmec;
	try {
		jcmec = nlohmann::json::parse(ifCMECjson);
	} catch (nlohmann::json::parse_error& e) {
		_EXCEPTION3("Malformed CMEC library file "
			"%s (%i) at byte position %i",
			e.what(), e.id, e.byte);
	}

	// Validate file
	validate_cmec_json(jcmec);

	// Output metadata
	std::string strName = jcmec["module"]["name"];
	for (int i = 0; i < strName.length(); i++) {
		if (!isalnum(strName[i]) && (strName[i] != '_')) {
			_EXCEPTION1("Invalid \"cmec.json\": Name \"%s\" must only contain alphanumeric characters",
				strName.c_str());
		}
	}
	std::string strLongName = jcmec["module"]["long_name"];
	Announce("Module \"%s\" (%s)", strName.c_str(), strLongName.c_str());

	// Load the CMEC library
	Announce("Reading CMEC library");
	CMECLibrary lib;
	lib.Read();

	// Add this path to the library
	Announce("Add new module to library");
	bool fSuccess = lib.Insert(strName, pathModule);
	if (!fSuccess) {
		return (-1);
	}

	// Write CMEC library
	Announce("Writing CMEC library");
	lib.Write();

	AnnounceEndBlock("Done");

	return 0;
}

///////////////////////////////////////////////////////////////////////////////

///	<summary>
///		Unregister the specified module.
///	</summary>
int cmec_unregister(
	const std::string & strModuleName
) {
	AnnounceStartBlock("Unregistering \"%s\"", strModuleName.c_str());

	// Load the CMEC library
	Announce("Reading CMEC library");
	CMECLibrary lib;
	lib.Read();

	// Remove module
	Announce("Removing module");
	bool fSuccess = lib.Remove(strModuleName);
	if (!fSuccess) {
		return (-1);
	}

	// Write CMEC library
	Announce("Writing CMEC library");
	lib.Write();

	return 0;
}

///////////////////////////////////////////////////////////////////////////////

///	<summary>
///		List available modules and configurations.
///	</summary>
int cmec_list(
	bool fListAll
) {
	// Load the CMEC library
	Announce("Reading CMEC library");
	CMECLibrary lib;
	lib.Read();

	// Check for size zero library
	if (lib.size() == 0) {
		Announce("CMEC library contains no entries");
		return 0;
	}

	// List modules
	AnnounceStartBlock("CMEC library contains the following modules:");
	for (auto it = lib.begin(); it != lib.end(); it++) {
		Announce("%s", it->first.c_str());
	}

	return 0;
}

///////////////////////////////////////////////////////////////////////////////

///	<summary>
///		Run the specified module.
///	</summary>
int cmec_run(
) {
	return 0;
}

///////////////////////////////////////////////////////////////////////////////

int main(int argc, char **argv) {

	try {

	// Executable
	std::string strExecutable = argv[0];

	// Command
	std::string strCommand;
	if (argc >= 2) {
		strCommand = argv[1];
	}

	// Arguments
	std::vector<std::string> vecArg;
	for (int c = 2; c < argc; c++) {
		vecArg.push_back(argv[c]);
	}

	// Register
	if (strCommand == "register") {
		if (argc == 3) {
			std::string strModuleDir = argv[2];
			return cmec_register(strModuleDir);

		} else {
			printf("Usage: %s register <module directory>\n", strExecutable.c_str());
			return 1;
		}
	}

	// Unregister
	if (strCommand == "unregister") {
		if (argc == 3) {
			std::string strModule = argv[1];
			return cmec_unregister(strModule);

		} else {
			printf("Usage: %s unregister <module name>\n", strExecutable.c_str());
			return 1;
		}
	}

	// List available modules
	if (strCommand == "list") {
		if (argc == 2) {
			return cmec_list(false);

		} else {
			printf("Usage: %s list\n", strExecutable.c_str());
			return 1;
		}
	}
 
	// Execute module(s)
	if (strCommand == "run") {
		if (argc == 4) {
			std::string strModules = argv[1];
			std::string strModelDir = argv[2];
			std::string strOutputDir = argv[3];
			return cmec_run();

		} else {
			printf("Usage: %s run [-o <obs dir>] <model dir> <output dir> <modules>\n", strExecutable.c_str());
			return 1;
		}
	}

	// Check command line arguments
	{
		printf("Usage:\n");
		printf("%s register <module directory>\n", strExecutable.c_str());
		printf("%s unregister <module name>\n", strExecutable.c_str());
		printf("%s list [all]\n", strExecutable.c_str());
		printf("%s remove-library\n", strExecutable.c_str());
		printf("%s run <modules> <model dir> <output dir>\n", strExecutable.c_str());
		return 1;
	}

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

