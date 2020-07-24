///////////////////////////////////////////////////////////////////////////////
///
///	\file    STLStringHelper.h
///	\author  Paul Ullrich
///	\version July 26, 2010
///
///	<remarks>
///		Copyright 2000-2010 Paul Ullrich
///
///		This file is distributed as part of the Tempest source code package.
///		Permission is granted to use, copy, modify and distribute this
///		source code and its documentation under the terms of the GNU General
///		Public License.  This software is provided "as is" without express
///		or implied warranty.
///	</remarks>

#ifndef _STLSTRINGHELPER_H_
#define _STLSTRINGHELPER_H_

#include <string>

#include <cstring>

///	<summary>
///		This class exposes additional functionality which can be used to
///		supplement the STL string class.
///	</summary>
class STLStringHelper {

///////////////////////////////////////////////////////////////////////////////

private:
STLStringHelper() { }

public:

///////////////////////////////////////////////////////////////////////////////

inline static void ToLower(std::string &str) {
	unsigned int i;
	for(i = 0; i < str.length(); i++) {
		str[i] = tolower(str[i]);
	}
}

///////////////////////////////////////////////////////////////////////////////

inline static void ToUpper(std::string &str) {
	unsigned int i;
	for(i = 0; i < str.length(); i++) {
		str[i] = toupper(str[i]);
	}
}

///////////////////////////////////////////////////////////////////////////////

///	<summary>
///		Wildcard matching function from StackExchange:
///		http://stackoverflow.com/questions/3300419/file-name-matching-with-wildcard
///	</summary>
static bool WildcardMatch(
	const char * needle,
	const char * haystack
) {
    for (; *needle!='\0'; ++needle) {
        switch (*needle) {
        case '?': ++haystack;   
                break;
        case '*': {
            size_t max = strlen(haystack);
            if (needle[1] == '\0' || max == 0)
                return true;
            for (size_t i = 0; i < max; i++)
                if (WildcardMatch(needle+1, haystack + i))
                    return true;
            return false;
        }
        default:
            if (*haystack != *needle)
                return false;
            ++haystack;
        }       
    }
    return (*haystack == '\0');
}

///////////////////////////////////////////////////////////////////////////////

};

#endif

