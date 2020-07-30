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

///	<summary>
///		Current code version.
///	</summary>
static const char * g_szVersion = "20200731";

///	<summary>
///		Name of the CMEC library file.
///	</summary>
static const char * g_szCMECLibraryName = ".cmeclibrary";

///	<summary>
///		Name of the CMEC TOC file.
///	</summary>
static const char * g_szCMECTOCName = "contents.json";

///	<summary>
///		Name of the CMEC settings file.
///	</summary>
static const char * g_szCMECSettingsName = "settings.json";

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

///	<summary>
///		A class representing the CMEC module library.
///	</summary>
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
			m_path = pathNamelist/filesystem::path(g_szCMECLibraryName);
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
		m_path = pathNamelist/filesystem::path(g_szCMECLibraryName);
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
				_EXCEPTIONT("Malformed CMEC library file: \"cmec-driver\" is not of type object");
			}

			auto itv = m_jlib.find("version");
			if (itv == m_jlib.end()) {
				_EXCEPTIONT("Malformed CMEC library file missing key \"version\"");
			}
			if (!itv->is_string()) {
				_EXCEPTIONT("Malformed CMEC library file: \"version\" is not of type string");
			}

			auto itm = m_jlib.find("modules");
			if (itm == m_jlib.end()) {
				_EXCEPTIONT("Malformed CMEC library file missing key \"modules\"");
			}
			if (!itm->is_object()) {
				_EXCEPTIONT("Malformed CMEC library file: \"modules\" is not of type object");
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

				std::string strModuleName(itmod.key());
				filesystem::path path(itmod.value());

				// Verify module doesn't exist already in map
				if (m_mapModulePaths.find(strModuleName) != m_mapModulePaths.end()) {
					_EXCEPTION1("Malformed CMEC library file: Repeated module name \"%s\"",
						strModuleName.c_str());
				}

				m_mapModulePaths.insert(
					std::pair<std::string, filesystem::path>(
						strModuleName, path));
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
			Announce("\033[1mERROR:\033[0m Module already exists in library; "
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
			Announce("\033[1mERROR:\033[0m Module \"%s\" not found in library",
				strModuleName.c_str());
			return false;
		}

		nlohmann::json & jmodules = m_jlib["modules"];
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

///	<summary>
///		A class representing the settings.json file.
///	</summary>
class CMECModuleSettings {

public:
	///	<summary>
	///		Check for the existence of a contents file.
	///	</summary>
	static bool ExistsInModulePath(
		const filesystem::path & pathModule
	) {
		filesystem::path pathSettings = pathModule / filesystem::path(g_szCMECSettingsName);
		return pathSettings.exists();
	}

public:
	///	<summary>
	///		Clear the CMEC module contents.
	///	</summary>
	void Clear() {
		m_path = filesystem::path();
		m_jsettings.clear();
	}

	///	<summary>
	///		Read the CMEC module contents file.
	///	</summary>
	bool Read(
		const filesystem::path & pathSettings
	) {
		// Clear the module contents
		Clear();

		// Store the settings.json file path
		m_path = pathSettings;

		// Get the path
		filesystem::path pathCMECjson = pathSettings;
		std::ifstream ifCMECjson(pathCMECjson.str());
		if (!ifCMECjson.is_open()) {
			_EXCEPTION1("Unable to open \"%s\"", pathSettings.str().c_str());
		}

		// Parse the CMEC settings json
		try {
			m_jsettings = nlohmann::json::parse(ifCMECjson);
		} catch (nlohmann::json::parse_error& e) {
			_EXCEPTION3("Malformed CMEC settings file "
				"%s (%i) at byte position %i",
				e.what(), e.id, e.byte);
		}

		// Validate the CMEC settings json

		// settings key
		auto its = m_jsettings.find("settings");
		if (its == m_jsettings.end()) {
			Announce("ERROR: Malformed CMEC settings file \"%s\": missing key \"settings\"",
				pathSettings.str().c_str());
			return false;
		}
		if (!its->is_object()) {
			Announce("ERROR: Malformed CMEC settings file \"%s\": \"settings\" is not of type object",
				pathSettings.str().c_str());
			return false;
		}

		auto itsn = its->find("name");
		if (itsn == its->end()) {
			Announce("ERROR: Malformed CMEC settings file \"%s\": missing key \"settings::name\"",
				pathSettings.str().c_str());
			return false;
		}
		if (!itsn->is_string()) {
			Announce("ERROR: Malformed CMEC settings file \"%s\": \"settings::name\" is not of type string",
				pathSettings.str().c_str());
			return false;
		}

		auto itsln = its->find("long_name");
		if (itsln == its->end()) {
			Announce("ERROR: Malformed CMEC settings file \"%s\": missing key \"settings::long_name\"",
				pathSettings.str().c_str());
			return false;
		}
		if (!itsln->is_string()) {
			Announce("ERROR: Malformed CMEC settings file \"%s\": \"settings::long_name\" is not of type string",
				pathSettings.str().c_str());
			return false;
		}

		auto itsd = its->find("driver");
		if (itsd == its->end()) {
			Announce("ERROR: Malformed CMEC settings file \"%s\": missing key \"settings::driver\"",
				pathSettings.str().c_str());
			return false;
		}
		if (!itsd->is_string()) {
			Announce("ERROR: Malformed CMEC settings file \"%s\": \"settings::driver\" is not of type string",
				pathSettings.str().c_str());
			return false;
		}

		// varlist key
		auto itv = m_jsettings.find("varlist");
		if (itv == m_jsettings.end()) {
			Announce("ERROR: Malformed CMEC settings file \"%s\": missing key \"varlist\"",
				pathSettings.str().c_str());
			return false;
		}
		if (!itv->is_object()) {
			Announce("ERROR: Malformed CMEC settings file \"%s\": \"varlist\" is not of type object",
				pathSettings.str().c_str());
			return false;
		}

		// obslist key
		auto ito = m_jsettings.find("obslist");
		if (ito == m_jsettings.end()) {
			Announce("ERROR: Malformed CMEC settings file \"%s\": missing key \"obslist\"",
				pathSettings.str().c_str());
			return false;
		}
		if (!ito->is_object()) {
			Announce("ERROR: Malformed CMEC settings file \"%s\": \"obslist\" is not of type object",
				pathSettings.str().c_str());
			return false;
		}

		return true;
	}

public:
	///	<summary>
	///		Name of the module.
	///	<summary>
	std::string GetName() const {
		return m_jsettings["settings"]["name"];
	}

	///	<summary>
	///		Long name of the module.
	///	</summary>
	std::string GetLongName() const {
		return m_jsettings["settings"]["long_name"];
	}

protected:
	///	<summary>
	///		Path to the CMEC module.
	///	</summary>
	filesystem::path m_path;

	///	<summary>
	///		JSON file representation of the CMEC TOC file.
	///	</summary>
	nlohmann::json m_jsettings;
};

///////////////////////////////////////////////////////////////////////////////

///	<summary>
///		A class representing the contents of a specific CMEC module.
///	</summary>
class CMECModuleTOC {

public:
	///	<summary>
	///		A map from module configurations to paths.
	///	</summary>
	typedef std::map<std::string, filesystem::path> ModuleConfigMap;

	///	<summary>
	///		A const_iterator into the map.
	///	</summary>
	typedef ModuleConfigMap::const_iterator const_iterator;

public:
	///	<summary>
	///		Check for the existence of a contents file.
	///	</summary>
	static bool ExistsInModulePath(
		const filesystem::path & pathModule
	) {
		filesystem::path pathContents = pathModule / filesystem::path(g_szCMECTOCName);
		return pathContents.exists();
	}

public:
	///	<summary>
	///		Clear the CMEC module contents.
	///	</summary>
	void Clear() {
		m_path = filesystem::path();
		m_mapConfigs.clear();
		m_jcmec.clear();
	}

	///	<summary>
	///		Read the CMEC module contents file.
	///	</summary>
	bool Read(
		const filesystem::path & pathModule
	) {
		// Clear the module contents
		Clear();

		// Get the path
		m_path = pathModule / filesystem::path(g_szCMECTOCName);
		std::ifstream ifCMECjson(m_path.str());
		if (!ifCMECjson.is_open()) {
			_EXCEPTION1("Unable to open \"%s\"", m_path.str().c_str());
		}

		// Parse the CMEC json
		try {
			m_jcmec = nlohmann::json::parse(ifCMECjson);
		} catch (nlohmann::json::parse_error& e) {
			_EXCEPTION3("Malformed CMEC config file "
				"%s (%i) at byte position %i",
				e.what(), e.id, e.byte);
		}

		// Validate the file
		auto itm = m_jcmec.find("module");
		if (itm == m_jcmec.end()) {
			Announce("ERROR: Malformed CMEC contents file \"%s\": missing key \"module\"",
				m_path.str().c_str());
			return false;
		}
		if (!itm->is_object()) {
			Announce("ERROR: Malformed CMEC contents file \"%s\": \"module\" is not of type object",
				m_path.str().c_str());
			return false;
		}
	
		nlohmann::json jmodule = *itm;
		auto itmn = jmodule.find("name");
		if (itmn == jmodule.end()) {
			Announce("ERROR: Malformed CMEC contents file \"%s\": missing key \"module::name\"",
				m_path.str().c_str());
			return false;
		}
		if (!itmn->is_string()) {
			Announce("ERROR: Malformed CMEC contents file \"%s\": \"module::name\" is not of type string",
				m_path.str().c_str());
			return false;
		}

		std::string strName = jmodule["name"];
		for (int i = 0; i < strName.length(); i++) {
			if (!isalnum(strName[i]) && (strName[i] != '_')) {
				Announce("ERROR: Malformed CMEC contents file \"%s\": \"module::name\" entry \"%s\" must only contain alphanumeric characters",
					m_path.str().c_str(),
					strName.c_str());
				return false;
			}
		}

		auto itml = jmodule.find("long_name");
		if (itml == jmodule.end()) {
			Announce("ERROR: Malformed CMEC contents file \"%s\": missing key \"module::long_name\"",
				m_path.str().c_str());
			return false;
		}
		if (!itml->is_string()) {
			Announce("ERROR: Malformed CMEC contents file \"%s\": \"module::long_name\" is not of type string",
				m_path.str().c_str());
			return false;

		}

		auto itc = m_jcmec.find("contents");
		if (itc == m_jcmec.end()) {
			Announce("ERROR: Malformed CMEC contents file \"%s\": missing key \"contents\"",
				m_path.str().c_str());
			return false;
		}
		if (!itc->is_array()) {
			Announce("ERROR: Malformed CMEC contents file \"%s\": \"contents\" is not of type array",
				m_path.str().c_str());
			return false;
		}

		// Load configurations
		nlohmann::json jcontents = *itc;
		for (auto itconfig = jcontents.begin(); itconfig != jcontents.end(); itconfig++) {
			if (!itconfig->is_string()) {
				_EXCEPTIONT("Malformed CMEC library file: an entry of the \"contents\" array is not of type string");
			}

			filesystem::path pathSettings = pathModule / std::string(*itconfig);

			CMECModuleSettings cmecsettings;
			bool fSuccess = cmecsettings.Read(pathSettings);
			if (fSuccess) {
				m_mapConfigs.insert(
					std::pair<std::string, filesystem::path>(
						cmecsettings.GetName(), pathSettings));
			}
		}

		return true;
	}

	///	<summary>
	///		Insert a new path into the TOC.
	///	</summary>
	bool Insert(
		const std::string & strConfigName,
		const filesystem::path & path
	) {
		// Verify config doesn't exist already
		if (m_mapConfigs.find(strConfigName) != m_mapConfigs.end()) {
			Announce("\033[1mERROR:\033[0m Repeated configuration name \"%s\"",
				strConfigName.c_str());

			return false;
		}

		// Insert module
		m_mapConfigs.insert(
			std::pair<std::string, filesystem::path>(
				strConfigName, path));

		m_jcmec["contents"][strConfigName] = path.str();

		return true;
	}

public:
	///	<summary>
	///		Name of the module.
	///	<summary>
	std::string GetName() const {
		return m_jcmec["module"]["name"];
	}

	///	<summary>
	///		Long name of the module.
	///	</summary>
	std::string GetLongName() const {
		return m_jcmec["module"]["long_name"];
	}

public:
	///	<summary>
	///		Number of modules in this library.
	///	</summary>
	size_t size() const {
		return m_mapConfigs.size();
	}

	///	<summary>
	///		Constant iterator into module map.
	///	</summary>
	ModuleConfigMap::const_iterator begin() const {
		return m_mapConfigs.begin();
	}

	///	<summary>
	///		Constant iterator into module map.
	///	</summary>
	ModuleConfigMap::const_iterator end() const {
		return m_mapConfigs.end();
	}

protected:
	///	<summary>
	///		Path to the CMEC module.
	///	</summary>
	filesystem::path m_path;

	///	<summary>
	///		Map of configuration names to settings.json files.
	///	</summary>
	ModuleConfigMap m_mapConfigs;

	///	<summary>
	///		JSON file representation of the CMEC TOC file.
	///	</summary>
	nlohmann::json m_jcmec;

};

///////////////////////////////////////////////////////////////////////////////

///	<summary>
///		Register the specified module directory.
///	</summary>
int cmec_register(
	const std::string & strDirectory
) {
	AnnounceStartBlock("Registering \"%s\"", strDirectory.c_str());

	// Check path for cmec.json
	filesystem::path pathModule(strDirectory);

	// Module name
	std::string strName;

	// Check if module contains a settings file
	if (CMECModuleSettings::ExistsInModulePath(pathModule)) {
		Announce("Validating %s", g_szCMECSettingsName);

		CMECModuleSettings cmecsettings;
		cmecsettings.Read(pathModule);

		strName = cmecsettings.GetName();

	// Check if module contains a contents file
	} else if (CMECModuleTOC::ExistsInModulePath(pathModule)) {
		Announce("Validating %s", g_szCMECTOCName);

		CMECModuleTOC cmectoc;
		cmectoc.Read(pathModule);

		// Output metadata
		strName = cmectoc.GetName();
		std::string strLongName = cmectoc.GetLongName();
		Announce("Module \033[1m%s\033[0m (\033[1m%s\033[0m)", strName.c_str(), strLongName.c_str());

		// Check number of configurations
		Announce("Contains \033[1m%lu configurations\033[0m:", cmectoc.size());
		AnnounceBanner();
		for (auto itconfig = cmectoc.begin(); itconfig != cmectoc.end(); itconfig++) {
			AnnounceNoIndent("  %s::%s", strName.c_str(), itconfig->first.c_str());
		}
		AnnounceBanner();

	// Both files missing; throw error
	} else {
		Announce("ERROR: Module path must contain \"%s\" or \"%s\"",
			g_szCMECTOCName,
			g_szCMECSettingsName);

		return (-1);
	}

	// Load the CMEC library
	Announce("Reading CMEC library");
	CMECLibrary lib;
	lib.Read();

	// Add this path to the library
	Announce("Adding new module to library");
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

	// Done
	AnnounceEndBlock("Done");

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
		Announce("CMEC library contains no modules");
		return 0;
	}

	// List modules
	Announce("CMEC library contains %lu modules:", lib.size());
	AnnounceBanner();
	for (auto it = lib.begin(); it != lib.end(); it++) {
		if (CMECModuleTOC::ExistsInModulePath(it->second)) {
			CMECModuleTOC cmectoc;
			cmectoc.Read(it->second);
			Announce("  %s [%lu configurations]", it->first.c_str(), cmectoc.size());
			if (fListAll) {
				for (auto itconfig = cmectoc.begin(); itconfig != cmectoc.end(); itconfig++) {
					Announce("  ..%s::%s", it->first.c_str(), itconfig->first.c_str());
				}
			}

		} else {
			Announce("  %s", it->first.c_str());
		}
	}
	AnnounceBanner();

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
			return cmec_unregister(vecArg[0]);

		} else {
			printf("Usage: %s unregister <module name>\n", strExecutable.c_str());
			return 1;
		}
	}

	// List available modules
	if (strCommand == "list") {
		if (argc == 2) {
			return cmec_list(false);

		} else if ((argc == 3) && (vecArg[0] == "all")) {
			return cmec_list(true);

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
			printf("Usage: %s run <obs dir> <model dir> <output dir> <modules>\n", strExecutable.c_str());
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

