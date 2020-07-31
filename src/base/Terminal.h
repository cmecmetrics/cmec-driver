///////////////////////////////////////////////////////////////////////////////
///
///	\file	Terminal.h
///	\author  Paul Ullrich
///	\version July 31, 2020
///

#ifndef _TERMINAL_H_
#define _TERMINAL_H_

#include "Exception.h"
#include <iostream>
#include <iomanip>
#include <fstream>
#include <cstdio>

#if defined(_WIN32)
//
#else
#include <termios.h>
#endif

namespace Terminal {

///////////////////////////////////////////////////////////////////////////////

char GetSingleCharacter() {

#if defined(_WIN32)
	_EXCEPTIONT("Not implemented");
#else
	struct termios t;
	struct termios t_saved;

	// Set terminal to single character mode.
	tcgetattr(fileno(stdin), &t);
	t_saved = t;
	t.c_lflag &= (~ICANON & ~ECHO);
	t.c_cc[VTIME] = 0;
	t.c_cc[VMIN] = 1;
	if (tcsetattr(fileno(stdin), TCSANOW, &t) < 0) {
		_EXCEPTIONT("Unable to set terminal to single character mode");
	}

	std::streambuf *pbuf = (std::cin).rdbuf();
	char c = pbuf->sbumpc();

    // Restore terminal mode.
    if (tcsetattr(fileno(stdin), TCSANOW, &t_saved) < 0) {
        _EXCEPTIONT("Unable to restore terminal mode");
    }

	return c;
#endif
}

///////////////////////////////////////////////////////////////////////////////

}; // namespace Terminal

#endif // _TERMINAL_H_

