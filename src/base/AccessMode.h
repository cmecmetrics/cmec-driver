///////////////////////////////////////////////////////////////////////////////
///
///	\file    AccessMode.h
///	\author  Paul Ullrich
///	\version March 27, 2017
///
///	<remarks>
///		Copyright 2016- Paul Ullrich
///
///		This file is distributed as part of the Tempest source code package.
///		Permission is granted to use, copy, modify and distribute this
///		source code and its documentation under the terms of the GNU General
///		Public License.  This software is provided "as is" without express
///		or implied warranty.
///	</remarks>

#ifndef _ACCESSMODE_H_
#define _ACCESSMODE_H_

///////////////////////////////////////////////////////////////////////////////

typedef int AccessMode;

static const AccessMode AccessMode_ReadOnly = 0;

static const AccessMode AccessMode_ReadWrite = 1;

static const AccessMode AccessMode_Create = 2;

///////////////////////////////////////////////////////////////////////////////

#endif

